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
        prompt = self._create_filename_parsing_prompt(cleaned_filename)
        try:
            response = self.client.generate(
                model=self.model,
                prompt=f"{self._get_system_prompt()}\n\n{prompt}",
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

    def _get_system_prompt(self) -> str:
        return """
You are an expert at parsing TV and anime episode filenames and extracting structured metadata. Your job is to extract the following information and return it as strict JSON:

- "show_name": The full show name as it appears in the filename. This may include dashes, alternate titles, or unusual letter sequences like "GQuuuuuuX" — these are not metadata tags or suffixes, but part of the true name.
- "season": The season number as an integer, or null if not explicitly present.
- "episode": The episode number as an integer, or null if not explicitly present.
- "confidence": A float between 0.0 and 1.0 that reflects how certain you are in ALL extracted fields.
- "reasoning": A short explanation that justifies each extracted field and explains why the confidence is high or low.

---

Important Rules:
1. There is never a valid scenario with a season number but no episode number. If a season is detected but no episode, return episode: null and reduce confidence sharply.
2. It is common for filenames to include only a show name and episode number. This is valid and should not be interpreted as season 1 unless explicitly stated.
3. Dashes (-) are commonly used separators, but they can also appear within show names. Use heuristics: if a dash is between the show title and a number, it may be a separator; if it's inside a quoted or known title structure, or if there are words on both sides of the dash, keep it in the title.
4. Show names are often in Japanese or English, and may contain underscores, romanization artifacts, or substitutions. Normalize to readable title case.
5. Season and episode numbers are always expressed using Arabic numerals, often formatted as:
   - S02E03 / SO2 EO3 / 2nd Season 03 / Ep 03 / - 03 / 03 / 3
6. Tags such as [GroupName], [1080p], [BDRip], and hex hashes like [89F3A28D] must be ignored.
7. If any field is unclear or inferred, confidence should not exceed 0.7.
8. The output MUST BE STRICT JSON, with no markdown, code blocks, or commentary. Return ONLY the raw JSON object.

---

Output Constraints:
- Return a valid JSON object with exactly these fields:
  - show_name: string
  - season: integer or null
  - episode: integer or null
  - confidence: float (0.0 to 1.0)
  - reasoning: string
- Do not include any markdown, code blocks, or commentary. Return only the raw JSON object.

---

Example 1:
Given:
[Erai-raws] Kidou Senshi Gundam GQuuuuuuX - 12 [1080p AMZN WEB-DL AVC EAC3][MultiSub][CC001E26].mkv

Return:
{
  "show_name": "Kidou Senshi Gundam GQuuuuuuX",
  "season": null,
  "episode": 12,
  "confidence": 0.95,
  "reasoning": "Episode number 12 appears clearly after the show name; no season is indicated. Full title retained with suffix."
}

Example 2:
Given:
[Asakura] Tensei Shitara Slime Datta Ken 3rd Season 49 [BDRip x265 IObit FLAC] [36E425AB].mkv

Return:
{
  "show_name": "Tensei Shitara Slime Datta Ken",
  "season": 3,
  "episode": 49,
  "confidence": 0.95,
  "reasoning": "Season number is explicitly stated as '3rd Season'"
}

Example 3:
Given:
[SubsPlease] Zatsu Tabi - That's Journey - 01 (1080p) [EC01EEB3].mkv

Return:
{
  "show_name": "Zatsu Tabi - That's Journey",
  "season": null,
  "episode": 1,
  "confidence": 0.80,
  "reasoning": "Episode number 1 appears clearly after the show name; no season is indicated. Full title retained with suffix."
}
""" 

    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable directory name for a given long name using the LLM.
        Fallback to truncation if LLM fails.
        """
        prompt = (
            f"Suggest a short, human-readable directory name (max {max_length} characters) for the following long directory name. "
            f"Avoid special characters and keep it unique and recognizable. Return only the name, no commentary.\n\n"
            f"Long name: {long_name}"
        )
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
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.error(f"ollama_implementation.py::suggest_short_name - LLM error: {e}.")
            return long_name[:max_length]

    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable filename for a given long filename using the LLM.
        Fallback to truncation if LLM fails.
        """
        prompt = (
            f"Suggest a short, human-readable filename (max {max_length} characters) for the following long filename. "
            f"Preserve key information like show name, season, episode, and extension. Avoid special characters. Return only the filename, no commentary.\n\n"
            f"Long filename: {long_name}"
        )
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
            return short_name or long_name[:max_length]
        except Exception as e:
            logger.error(f"ollama_implementation.py::suggest_short_filename - LLM error: {e}.")
            return long_name[:max_length] 