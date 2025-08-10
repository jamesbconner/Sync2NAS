import logging
import re
import json
from typing import Dict, Any, List, Optional
from services.llm_implementations.llm_interface import LLMInterface
import os

logger = logging.getLogger(__name__)

class BaseLLMService(LLMInterface):
    """
    Base class for LLM-based filename parsing services.

    Provides shared logic for prompt loading, result validation, fallback parsing, and batch operations.

    Attributes:
        PROMPT_DIR (str): Directory containing prompt templates.

    Methods:
        load_prompt(prompt_name): Load a prompt template by name.
        _validate_and_clean_result(result, original_filename): Validate and clean LLM response.
        _fallback_parse(filename): Fallback parsing if LLM fails.
        _clean_filename_for_llm(filename): Clean filename for LLM processing.
        batch_parse_filenames(filenames, max_tokens): Parse multiple filenames in batch.
        suggest_show_name(show_name, detailed_results): Suggest best show match from TMDB results.
    """
    PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")

    def load_prompt(self, prompt_name: str) -> str:
        """
        Load a prompt template by name.

        Args:
            prompt_name (str): The name of the prompt file (e.g., "parse_filename").

        Returns:
            str: The content of the prompt file.

        Raises:
            FileNotFoundError: If the prompt file does not exist.
        """
        prompt_path = os.path.join(self.PROMPT_DIR, f"{prompt_name}.txt")
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _create_filename_parsing_prompt(self, filename: str) -> str:
        """
        Create a prompt for filename parsing.

        Args:
            filename (str): The filename to parse.

        Returns:
            str: The formatted prompt.
        """
        prompt_template = self.load_prompt('parse_filename')
        return prompt_template.format(filename=filename)

    def _validate_and_clean_result(self, result: Dict[str, Any], original_filename: str) -> Dict[str, Any]:
        """
        Validate and clean the LLM response.

        Args:
            result (Dict[str, Any]): Raw LLM response.
            original_filename (str): Original filename for fallback.

        Returns:
            dict: Validated and cleaned result.

        Raises:
            ValueError: If data types are invalid.
        """
        validated = {
            "show_name": result.get("show_name", "").strip(),
            "season": result.get("season"),
            "episode": result.get("episode"),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", "No reasoning provided")
        }
        # Preserve optional hash if present from LLM output
        if "hash" in result and isinstance(result.get("hash"), str):
            validated["hash"] = result.get("hash")
        try:
            if validated["season"] is not None:
                validated["season"] = int(validated["season"])
            if validated["episode"] is not None:
                validated["episode"] = int(validated["episode"])
            validated["confidence"] = float(validated["confidence"])
        except (ValueError, TypeError):
            logger.warning(f"Invalid data types in LLM response, using fallback")
            return self._fallback_parse(original_filename)
        validated["confidence"] = max(0.0, min(1.0, validated["confidence"]))
        if not validated["show_name"]:
            logger.warning(f"Empty show name from LLM, using fallback")
            return self._fallback_parse(original_filename)
        return validated

    def _fallback_parse(self, filename: str) -> Dict[str, Any]:
        """
        Fallback parsing when LLM fails.

        Args:
            filename (str): Original filename.

        Returns:
            dict: Fallback parsing result.
        """
        logger.info(f"Using fallback parsing for: {filename}")
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

    def _clean_filename_for_llm(self, filename: str) -> str:
        """
        Clean filename for better LLM processing.

        Args:
            filename (str): Raw filename.

        Returns:
            str: Cleaned filename.
        """
        base = re.sub(r"\.[a-z0-9]{2,4}$", "", filename, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[.*?\]", "", base)
        cleaned = re.sub(r"\(.*?\)", "", cleaned)
        cleaned = re.sub(r"[_.]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def batch_parse_filenames(self, filenames: List[str], max_tokens: int = 150) -> List[Dict[str, Any]]:
        """
        Parse multiple filenames in batch.

        Args:
            filenames (List[str]): List of filenames to parse.
            max_tokens (int): Maximum tokens per response.

        Returns:
            list: List of parsing results.
        """
        logger.info(f"Parsing {len(filenames)} filenames")
        results = []
        for filename in filenames:
            result = self.parse_filename(filename, max_tokens)
            results.append({
                "filename": filename,
                "parsed": result
            })
        return results

    def suggest_show_name(self, show_name: str, detailed_results: list) -> dict:
        """
        Suggest the best show match and English name from TMDB results using the LLM.
        Should return a dict with keys: tmdb_id, show_name
        """
        raise NotImplementedError("LLM implementation must override suggest_show_name") 