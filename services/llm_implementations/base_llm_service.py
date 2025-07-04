import logging
import re
import json
from typing import Dict, Any, List, Optional
from services.llm_implementations.llm_interface import LLMInterface
import os

logger = logging.getLogger(__name__)

class BaseLLMService(LLMInterface):
    PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")

    def load_prompt(self, prompt_name: str) -> str:
        prompt_path = os.path.join(self.PROMPT_DIR, f"{prompt_name}.txt")
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _validate_and_clean_result(self, result: Dict[str, Any], original_filename: str) -> Dict[str, Any]:
        """
        Validate and clean the LLM response.
        Args:
            result: Raw LLM response
            original_filename: Original filename for fallback
        Returns:
            dict: Validated and cleaned result
        """
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
            logger.warning(f"base_llm_service.py::_validate_and_clean_result - Invalid data types in LLM response, using fallback")
            return self._fallback_parse(original_filename)
        validated["confidence"] = max(0.0, min(1.0, validated["confidence"]))
        if not validated["show_name"]:
            logger.warning(f"base_llm_service.py::_validate_and_clean_result - Empty show name from LLM, using fallback")
            return self._fallback_parse(original_filename)
        return validated

    def _fallback_parse(self, filename: str) -> Dict[str, Any]:
        """
        Fallback parsing when LLM fails.
        Args:
            filename: Original filename
        Returns:
            dict: Fallback parsing result
        """
        logger.info(f"base_llm_service.py::_fallback_parse - Using fallback parsing for: {filename}")
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
            filename: Raw filename
        Returns:
            str: Cleaned filename
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
            filenames: List of filenames to parse
            max_tokens: Maximum tokens per response
        Returns:
            list: List of parsing results
        """
        logger.info(f"{self.__class__.__name__}::batch_parse_filenames - Parsing {len(filenames)} filenames")
        results = []
        for filename in filenames:
            result = self.parse_filename(filename, max_tokens)
            results.append({
                "filename": filename,
                "parsed": result
            })
        return results 