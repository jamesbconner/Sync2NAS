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
        prompt = self._create_filename_parsing_prompt(cleaned_filename)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
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

    def _get_system_prompt(self) -> str:
        return """You are an expert at parsing TV show filenames. Your task is to extract the show name, season number, and episode number from filenames.

IMPORTANT RULES:
1. Return ONLY valid JSON with the exact structure shown below
2. Show names should be the official/canonical name, not release group names
3. Season and episode numbers should be integers or null
4. Confidence should be a float between 0.0 and 1.0
5. Reasoning should explain your parsing decision

EXAMPLES:
- 'Breaking.Bad.S01E01.1080p.mkv' → {\"show_name\": \"Breaking Bad\", \"season\": 1, \"episode\": 1, \"confidence\": 0.95, \"reasoning\": \"Clear S01E01 format\"}
- 'One.Piece.Episode.1000.1080p.mkv' → {\"show_name\": \"One Piece\", \"season\": null, \"episode\": 1000, \"confidence\": 0.9, \"reasoning\": \"Episode number without season\"}
- 'Game.of.Thrones.S08E06.1080p.mkv' → {\"show_name\": \"Game of Thrones\", \"season\": 8, \"episode\": 6, \"confidence\": 0.95, \"reasoning\": \"Standard S08E06 format\"}

RESPONSE FORMAT:
{
    'show_name': 'string',
    'season': integer or null,
    'episode': integer or null,
    'confidence': float (0.0-1.0),
    'reasoning': 'string'
}"""

    def _create_filename_parsing_prompt(self, filename: str) -> str:
        return (f"Parse this TV show filename and extract the show name, season, and episode information:\n\n"
                f"Filename: {filename}\n\n"
                "Please analyze this filename and return the parsed information in JSON format.")

    def _validate_and_clean_result(self, result: Dict[str, Any], original_filename: str) -> Dict[str, Any]:
        validated = {
            "show_name": result.get("show_name", "").strip(),
            "season": result.get("season"),
            "episode": result.get("episode"),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", "No reasoning provided")
        }
        try:
            if validated["season"] is not None:
                validated["season"] = int(validated["season"])
            if validated["episode"] is not None:
                validated["episode"] = int(validated["episode"])
            validated["confidence"] = float(validated["confidence"])
        except (ValueError, TypeError):
            logger.warning(f"openai_implementation.py::_validate_and_clean_result - Invalid data types in LLM response, using fallback")
            return self._fallback_parse(original_filename)
        validated["confidence"] = max(0.0, min(1.0, validated["confidence"]))
        if not validated["show_name"]:
            logger.warning(f"openai_implementation.py::_validate_and_clean_result - Empty show name from LLM, using fallback")
            return self._fallback_parse(original_filename)
        return validated

    def _fallback_parse(self, filename: str) -> Dict[str, Any]:
        logger.info(f"openai_implementation.py::_fallback_parse - Using fallback parsing for: {filename}")
        base = re.sub(r"\.[a-z0-9]{2,4}$", "", filename, flags=re.IGNORECASE)
        cleaned = re.sub(r"[\[\(].*?[\]\)]", "", base)
        cleaned = re.sub(r"[_.]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        season_episode_pattern = r"(.*?)[\s\-]+[Ss](\d{1,2})[Ee](\d{1,3})"
        match = re.search(season_episode_pattern, cleaned, re.IGNORECASE)
        if match:
            show_name = match.group(1).strip(" -_")
            season = int(match.group(2))
            episode = int(match.group(3))
            return {
                "show_name": show_name,
                "season": season,
                "episode": episode,
                "confidence": 0.5,
                "reasoning": "Fallback regex parsing"
            }
        return {
            "show_name": cleaned,
            "season": None,
            "episode": None,
            "confidence": 0.1,
            "reasoning": "Fallback parsing - no clear pattern"
        } 