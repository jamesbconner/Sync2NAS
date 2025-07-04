import logging
import json
import re
from typing import Dict, Any, List, Optional
import openai
from utils.sync2nas_config import load_configuration
from services.llm_implementations.base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)

class OpenAILLMService(BaseLLMService):
    """
    LLM service implementation using OpenAI's GPT models.
    Provides filename parsing for show metadata extraction.
    """
    def __init__(self, config):
        """
        Initialize the OpenAI LLM service.
        Args:
            config: Loaded configuration object
        """
        self.config = config
        self.model = self.config.get('openai', 'model', fallback='gpt-3.5-turbo')
        self.api_key = self.config.get('openai', 'api_key', fallback=None)
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set it in config file.")
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        logger.info(f"openai_implementation.py::__init__ - OpenAI LLM service initialized with model: {self.model}")

    def parse_filename(self, filename: str, max_tokens: int = 150) -> Dict[str, Any]:
        """
        Parse a filename using OpenAI LLM to extract show metadata.
        Args:
            filename: Raw filename to parse
            max_tokens: Maximum tokens for LLM response
        Returns:
            dict: Parsed metadata
        """
        logger.info(f"openai_implementation.py::parse_filename - Parsing filename with OpenAI LLM: {filename}")
        cleaned_filename = self._clean_filename_for_llm(filename)
        system_prompt = self.load_prompt('parse_filename')
        user_prompt = self.load_prompt('parse_filename').format(filename=cleaned_filename)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            logger.debug(f"openai_implementation.py::parse_filename - OpenAI response: {content}")
            try:
                result = json.loads(content)
                parsed_result = self._validate_and_clean_result(result, filename)
                logger.info(f"openai_implementation.py::parse_filename - Successfully parsed: {parsed_result}")
                return parsed_result
            except json.JSONDecodeError as e:
                logger.error(f"openai_implementation.py::parse_filename - Failed to parse JSON response: {e}")
                return self._fallback_parse(filename)
        except Exception as e:
            logger.exception(f"openai_implementation.py::parse_filename - OpenAI API error: {e}")
            return self._fallback_parse(filename)

    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable directory name for a given long name using the LLM.
        Fallback to truncation if LLM fails.
        """
        prompt = self.load_prompt('suggest_short_dirname')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at generating short, unique directory names."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length,
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()
            short_name = content.splitlines()[0][:max_length]
            short_name = re.sub(r'[^\w\- ]', '', short_name)
            logger.debug(f"openai_implementation.py::suggest_short_dirname - LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.error(f"openai_implementation.py::suggest_short_name - LLM error: {e}.")
            return long_name[:max_length]

    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable filename for a given long filename using the LLM.
        Fallback to truncation if LLM fails.
        """
        prompt = self.load_prompt('suggest_short_filename')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at generating short, unique filenames."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length,
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()
            short_name = content.splitlines()[0][:max_length]
            short_name = re.sub(r'[^\w\-. ]', '', short_name)
            logger.debug(f"openai_implementation.py::suggest_short_filename - LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.error(f"openai_implementation.py::suggest_short_filename - LLM error: {e}.")
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
        logger.debug(f"openai_implementation.py::suggest_show_name - Candidates: {candidates}")
        prompt_template = self.load_prompt('select_show_name')
        candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
        prompt = prompt_template.format(show_name=show_name, candidates=candidates_json)
        logger.debug(f"openai_implementation.py::suggest_show_name - Prompt: {prompt}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at selecting the best TV show match from TMDB results."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=256,
                temperature=0.1
            )
            content = response.choices[0].message.content
            logger.debug(f"openai_implementation.py::suggest_show_name - LLM response: {content}")
            result = json.loads(content)
            if 'tmdb_id' in result and 'show_name' in result:
                return result
        except Exception as e:
            logger.error(f"openai_implementation.py::suggest_show_name - LLM error: {e}")
        first = candidates[0]
        return {'tmdb_id': first['id'], 'show_name': first['name']} 