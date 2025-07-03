from configparser import ConfigParser
from typing import Dict, List
import anthropic
import logging
from services.llm_implementations.base_llm_service import BaseLLMService

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
        prompt = self._create_filename_parsing_prompt(filename)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self._get_system_prompt(),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        text = response.content[0].text if response.content else ""
        return self._validate_and_clean_result(text, filename)

    def batch_parse_filenames(self, filenames: List[str]) -> List[Dict]:
        return super().batch_parse_filenames(filenames)

    def _get_system_prompt(self) -> str:
        return (
            "You are an expert at parsing anime file names. "
            "Return a JSON object with keys 'show_name', 'season', and 'episode'. "
            "Use numeric values for season and episode. Do not include extra commentary."
        )
