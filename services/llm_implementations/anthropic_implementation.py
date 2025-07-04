from configparser import ConfigParser
from typing import Dict, List
import anthropic
import logging
from services.llm_implementations.base_llm_service import BaseLLMService
import re
import json

logger = logging.getLogger(__name__)

class AnthropicLLMService(BaseLLMService):
    """
    LLM service implementation using Anthropic's Claude models.
    Provides filename parsing for show metadata extraction.
    """
    def __init__(self, config):
        """
        Initialize the Anthropic LLM service.
        Args:
            config: Loaded configuration object
        """
        self.config = config
        self.model = self.config.get("anthropic", "model", fallback="claude-3-sonnet-20240229")
        self.api_key = self.config.get("anthropic", "api_key", fallback=None)
        self.max_tokens = self.config.getint("anthropic", "max_tokens", fallback=200)
        self.temperature = self.config.getfloat("anthropic", "temperature", fallback=0.1)
        self.confidence_threshold = self.config.getfloat("anthropic", "llm_confidence_threshold", fallback=0.7)
        
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set it in config file.")
        
        if not isinstance(self.max_tokens, int):
            raise TypeError("Anthropic max_tokens must be an integer")
        if not isinstance(self.temperature, float):
            raise TypeError("Anthropic temperature must be a float")
        if not isinstance(self.confidence_threshold, float):
            raise TypeError("Anthropic confidence_threshold must be a float")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        logger.info(f"anthropic_implementation.py::__init__ - Anthropic LLM service initialized with model: {self.model}")


    def parse_filename(self, filename: str) -> Dict:
        cleaned_filename = self._clean_filename_for_llm(filename)
        system_prompt = self.load_prompt('parse_filename')
        user_prompt = self.load_prompt('parse_filename').format(filename=cleaned_filename)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        text = response.content[0].text if response.content else ""
        return self._validate_and_clean_result(text, filename)

    def batch_parse_filenames(self, filenames: List[str]) -> List[Dict]:
        return super().batch_parse_filenames(filenames)

    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable directory name for a given long name using the LLM.
        Fallback to truncation if LLM fails.
        """
        prompt = self.load_prompt('suggest_short_dirname')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_length,
                temperature=self.temperature,
                system="You are an expert at generating short, unique directory names.",
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip() if response.content else ""
            short_name = text.splitlines()[0][:max_length]
            short_name = re.sub(r'[^\w\- ]', '', short_name)
            logger.debug(f"anthropic_implementation.py::suggest_short_dirname - LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.error(f"anthropic_implementation.py::suggest_short_name - LLM error: {e}.")
            return long_name[:max_length]

    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable filename for a given long filename using the LLM.
        Fallback to truncation if LLM fails.
        """
        prompt = self.load_prompt('suggest_short_filename')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_length,
                temperature=self.temperature,
                system="You are an expert at generating short, unique filenames.",
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip() if response.content else ""
            short_name = text.splitlines()[0][:max_length]
            short_name = re.sub(r'[^\w\-. ]', '', short_name)
            logger.debug(f"anthropic_implementation.py::suggest_short_filename - LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.error(f"anthropic_implementation.py::suggest_short_filename - LLM error: {e}.")
            return long_name[:max_length]

    def suggest_show_name(self, show_name: str, detailed_results: list) -> dict:
        candidates = []
        for det in detailed_results:
            info = det.get('info', {})
            candidates.append({
                'id': info.get('id'),
                'tmdb_id': info.get('id'),
                'name': info.get('name'),
                'original_name': info.get('original_name'),
                'first_air_date': info.get('first_air_date'),
                'overview': info.get('overview'),
                'alternative_titles': det.get('alternative_titles', {}).get('results', [])
            })
        logger.debug(f"anthropic_implementation.py::suggest_show_name - Candidates: {candidates}")
        prompt_template = self.load_prompt('select_show_name')
        candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
        prompt = prompt_template.format(show_name=show_name, candidates=candidates_json)
        logger.debug(f"anthropic_implementation.py::suggest_show_name - Prompt: {prompt}")
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                temperature=self.temperature,
                system="You are an expert at selecting the best TV show match from TMDB results.",
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text if response.content else ""
            logger.debug(f"anthropic_implementation.py::suggest_show_name - LLM response: {text}")
            result = json.loads(text)
            if 'tmdb_id' in result and 'show_name' in result:
                return result
        except Exception as e:
            logger.error(f"anthropic_implementation.py::suggest_show_name - LLM error: {e}")
        first = candidates[0]
        return {'tmdb_id': first['id'], 'show_name': first['name']}
