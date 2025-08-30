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

    Provides filename parsing, directory/filename suggestion, and show name selection using LLM.

    Attributes:
        config (ConfigParser): Configuration object.
        model (str): Model name used by Anthropic.
        api_key (str): API key for Anthropic.
        max_tokens (int): Maximum tokens for LLM responses.
        temperature (float): Temperature for LLM responses.
        confidence_threshold (float): Confidence threshold for LLM suggestions.
        client (Anthropic): Anthropic client instance.
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
            logger.exception("Anthropic API key is required. Set it in config file.")
            raise ValueError("Anthropic API key is required. Set it in config file.")
        
        if not isinstance(self.max_tokens, int):
            logger.exception("Anthropic max_tokens must be an integer")
            raise TypeError("Anthropic max_tokens must be an integer")
        if not isinstance(self.temperature, float):
            logger.exception("Anthropic temperature must be a float")
            raise TypeError("Anthropic temperature must be a float")
        if not isinstance(self.confidence_threshold, float):
            logger.exception("Anthropic confidence_threshold must be a float")
            raise TypeError("Anthropic confidence_threshold must be a float")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        logger.info(f"Anthropic LLM service initialized with model: {self.model}")


    def parse_filename(self, filename: str, max_tokens: int = 150) -> Dict:
        """
        Parses a filename to extract show metadata using the LLM.
        Args:
            filename (str): The filename to parse.
        Returns:
            Dict: A dictionary containing parsed show metadata.
        Raises:
            ValueError: If the LLM response does not meet the confidence threshold.
        """
        cleaned_filename = self._clean_filename_for_llm(filename)
        system_prompt = self.load_prompt('parse_filename')
        user_prompt = self.load_prompt('parse_filename').format(filename=cleaned_filename)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        text = response.content[0].text if response.content else ""
        try:
            result = json.loads(text)
            return self._validate_and_clean_result(result, filename)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return self._fallback_parse(filename)

    def batch_parse_filenames(self, filenames: List[str]) -> List[Dict]:
        """
        Parses a batch of filenames using the LLM.
        Args:
            filenames (List[str]): List of filenames to parse.
        Returns:
            List[Dict]: A list of dictionaries containing parsed show metadata.
        """
        return super().batch_parse_filenames(filenames)

    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable directory name for a given long name using the LLM.
        Args:
            long_name (str): The long name to suggest a short name for.
            max_length (int): The maximum length of the suggested name.
        Returns:
            str: A short, human-readable directory name.
        Raises:
            Exception: If the LLM fails to provide a suggestion.
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
            logger.debug(f"LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.exception(f"LLM error: {e}.")
            return long_name[:max_length]

    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable filename for a given long filename using the LLM.
        Args:
            long_name (str): The long filename to suggest a short name for.
            max_length (int): The maximum length of the suggested name.
        Returns:
            str: A short, human-readable filename.
        Raises:
            Exception: If the LLM fails to provide a suggestion.
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
            logger.debug(f"LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.exception(f"LLM error: {e}.")
            return long_name[:max_length]

    def suggest_show_name(self, show_name: str, detailed_results: list) -> dict:
        """
        Selects the best TV show match from TMDB results using the LLM.
        Args:
            show_name (str): The original show name.
            detailed_results (list): List of detailed TMDB results.
        Returns:
            dict: A dictionary containing the selected show's TMDB ID and name.
        Raises:
            Exception: If the LLM fails to provide a selection.
        """
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
        logger.debug(f"Candidates: {candidates}")
        prompt_template = self.load_prompt('select_show_name')
        candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
        prompt = prompt_template.format(show_name=show_name, candidates=candidates_json)
        logger.debug(f"Prompt: {prompt}")
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                temperature=self.temperature,
                system="You are an expert at selecting the best TV show match from TMDB results.",
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text if response.content else ""
            logger.debug(f"LLM response: {text}")
            result = json.loads(text)
            if 'tmdb_id' in result and 'show_name' in result:
                return result
        except Exception as e:
            logger.exception(f"LLM error: {e}")
        first = candidates[0]
        return {'tmdb_id': first['id'], 'show_name': first['name']}
