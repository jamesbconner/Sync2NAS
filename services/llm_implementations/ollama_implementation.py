import logging
import json
import re
from typing import Dict, Any, List
from ollama import Client
from utils.sync2nas_config import load_configuration
from services.llm_implementations.base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)

class OllamaLLMService(BaseLLMService):
    """
    LLM service implementation using a local Ollama server and model.
    Provides filename parsing for show metadata extraction.
    """
    def __init__(self, config):
        """
        Initialize the Ollama LLM service.
        Args:
            config: Loaded configuration object
        """
        self.config = config
        self.model = self.config.get('ollama', 'model', fallback='llama3.2')
        self.client = Client()
        logger.info(f"ollama_implementation.py::__init__ - Ollama LLM service initialized with model: {self.model}")

    def parse_filename(self, filename: str, max_tokens: int = 150) -> Dict[str, Any]:
        """
        Parse a filename using Ollama LLM to extract show metadata.
        Args:
            filename: Raw filename to parse
            max_tokens: Maximum tokens for LLM response
        Returns:
            dict: Parsed metadata
        """
        logger.info(f"ollama_implementation.py::parse_filename - Parsing filename with Ollama LLM: {filename}")
        cleaned_filename = self._clean_filename_for_llm(filename)
        prompt = self.load_prompt('parse_filename').format(filename=cleaned_filename)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={"num_predict": max_tokens, "temperature": 0.1}
            )
            # Extract the JSON string from the response object
            if hasattr(response, 'response'):
                content = response.response
            elif isinstance(response, dict) and 'response' in response:
                content = response['response']
            else:
                content = response  # fallback
            logger.debug(f"ollama_implementation.py::parse_filename - Ollama response: {content}")
            try:
                result = json.loads(content)
                parsed_result = self._validate_and_clean_result(result, filename)
                logger.info(f"ollama_implementation.py::parse_filename - Successfully parsed: {parsed_result}")
                return parsed_result
            except json.JSONDecodeError as e:
                logger.error(f"ollama_implementation.py::parse_filename - Failed to parse JSON response: {e}")
                return self._fallback_parse(filename)
        except Exception as e:
            logger.exception(f"ollama_implementation.py::parse_filename - Ollama API error: {e}")
            return self._fallback_parse(filename)

    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable directory name for a given long name using the LLM.
        Fallback to truncation if LLM fails.
        """
        prompt = self.load_prompt('suggest_short_dirname')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={"num_predict": max_length, "temperature": 0.1}
            )
            if hasattr(response, 'response'):
                content = response.response.strip()
            elif isinstance(response, dict) and 'response' in response:
                content = response['response'].strip()
            else:
                content = str(response).strip()
            # Only keep the first line and truncate if needed
            short_name = content.splitlines()[0][:max_length]
            # Remove problematic characters
            short_name = re.sub(r'[^\w\- ]', '', short_name)
            logger.debug(f"ollama_implementation.py::suggest_short_dirname - LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.error(f"ollama_implementation.py::suggest_short_name - LLM error: {e}.")
            return long_name[:max_length]

    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable filename for a given long filename using the LLM.
        Fallback to truncation if LLM fails.
        """
        prompt = self.load_prompt('suggest_short_filename')
        prompt = prompt.format(max_length=max_length, long_name=long_name)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={"num_predict": max_length, "temperature": 0.1}
            )
            if hasattr(response, 'response'):
                content = response.response.strip()
            elif isinstance(response, dict) and 'response' in response:
                content = response['response'].strip()
            else:
                content = str(response).strip()
            short_name = content.splitlines()[0][:max_length]
            short_name = re.sub(r'[^\w\-. ]', '', short_name)
            logger.debug(f"ollama_implementation.py::suggest_short_filename - LLM recommended: {short_name}")
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.error(f"ollama_implementation.py::suggest_short_filename - LLM error: {e}.")
            return long_name[:max_length] 