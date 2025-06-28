"""
LLM Service Module

This module provides LLM-based filename parsing using OpenAI's GPT models.
It handles show name extraction from filenames with better accuracy than regex patterns.
"""

import logging
import json
import re
from typing import Dict, Optional, Any
import openai
from utils.sync2nas_config import load_configuration

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for LLM-based filename parsing and show identification.
    
    Uses OpenAI's GPT models to intelligently extract show names, seasons,
    and episodes from filenames with better accuracy than regex patterns.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the LLM service.
        
        Args:
            api_key: OpenAI API key (if None, will try to load from config)
            model: OpenAI model to use (default: gpt-3.5-turbo)
        """
        self.model = model
        
        # Load API key from config if not provided
        if not api_key:
            try:
                config = load_configuration('./config/sync2nas_config.ini')
                api_key = config.get("OpenAI", "api_key", fallback=None)
            except Exception as e:
                logger.warning(f"services/llm_service.py::__init__ - Could not load API key from config: {e}")
        
        if not api_key:
            raise ValueError("OpenAI API key is required. Set it in config file or pass to constructor.")
        
        # Initialize OpenAI client
        openai.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)
        
        logger.info(f"services/llm_service.py::__init__ - LLM service initialized with model: {model}")

    def parse_filename(self, filename: str, max_tokens: int = 150) -> Dict[str, Any]:
        """
        Parse a filename using LLM to extract show metadata.
        
        Args:
            filename: Raw filename to parse
            max_tokens: Maximum tokens for LLM response
            
        Returns:
            dict: {
                "show_name": str,
                "season": int | None,
                "episode": int | None,
                "confidence": float,
                "reasoning": str
            }
        """
        logger.info(f"services/llm_service.py::parse_filename - Parsing filename with LLM: {filename}")
        
        # Clean the filename for better LLM processing
        cleaned_filename = self._clean_filename_for_llm(filename)
        
        # Create the prompt
        prompt = self._create_filename_parsing_prompt(cleaned_filename)
        
        try:
            # Call the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.1,  # Low temperature for consistent parsing
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            # Parse the response
            content = response.choices[0].message.content
            logger.debug(f"services/llm_service.py::parse_filename - LLM response: {content}")
            
            # Parse JSON response
            try:
                result = json.loads(content)
                
                # Validate and clean the result
                parsed_result = self._validate_and_clean_result(result, filename)
                
                logger.info(f"services/llm_service.py::parse_filename - Successfully parsed: {parsed_result}")
                return parsed_result
                
            except json.JSONDecodeError as e:
                logger.error(f"services/llm_service.py::parse_filename - Failed to parse JSON response: {e}")
                return self._fallback_parse(filename)
                
        except Exception as e:
            logger.exception(f"services/llm_service.py::parse_filename - LLM API error: {e}")
            return self._fallback_parse(filename)

    def _clean_filename_for_llm(self, filename: str) -> str:
        """
        Clean filename for better LLM processing.
        
        Args:
            filename: Raw filename
            
        Returns:
            str: Cleaned filename
        """
        # Remove file extension
        base = re.sub(r"\.[a-z0-9]{2,4}$", "", filename, flags=re.IGNORECASE)
        
        # Remove common release group tags and metadata
        # Keep some useful information but remove noise
        cleaned = re.sub(r"\[.*?\]", "", base)  # Remove [tags]
        cleaned = re.sub(r"\(.*?\)", "", base)  # Remove (metadata)
        
        # Normalize delimiters
        cleaned = re.sub(r"[_.]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        return cleaned

    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for filename parsing.
        
        Returns:
            str: System prompt
        """
        return """You are an expert at parsing TV show filenames. Your task is to extract the show name, season number, and episode number from filenames.

IMPORTANT RULES:
1. Return ONLY valid JSON with the exact structure shown below
2. Show names should be the official/canonical name, not release group names
3. Season and episode numbers should be integers or null
4. Confidence should be a float between 0.0 and 1.0
5. Reasoning should explain your parsing decision

EXAMPLES:
- "Breaking.Bad.S01E01.1080p.mkv" → {"show_name": "Breaking Bad", "season": 1, "episode": 1, "confidence": 0.95, "reasoning": "Clear S01E01 format"}
- "One.Piece.Episode.1000.1080p.mkv" → {"show_name": "One Piece", "season": null, "episode": 1000, "confidence": 0.9, "reasoning": "Episode number without season"}
- "Game.of.Thrones.S08E06.1080p.mkv" → {"show_name": "Game of Thrones", "season": 8, "episode": 6, "confidence": 0.95, "reasoning": "Standard S08E06 format"}

RESPONSE FORMAT:
{
    "show_name": "string",
    "season": integer or null,
    "episode": integer or null,
    "confidence": float (0.0-1.0),
    "reasoning": "string"
}"""

    def _create_filename_parsing_prompt(self, filename: str) -> str:
        """
        Create the user prompt for filename parsing.
        
        Args:
            filename: Cleaned filename
            
        Returns:
            str: User prompt
        """
        return f"""Parse this TV show filename and extract the show name, season, and episode information:

Filename: {filename}

Please analyze this filename and return the parsed information in JSON format."""

    def _validate_and_clean_result(self, result: Dict[str, Any], original_filename: str) -> Dict[str, Any]:
        """
        Validate and clean the LLM response.
        
        Args:
            result: Raw LLM response
            original_filename: Original filename for fallback
            
        Returns:
            dict: Validated and cleaned result
        """
        # Ensure all required fields exist
        validated = {
            "show_name": result.get("show_name", "").strip(),
            "season": result.get("season"),
            "episode": result.get("episode"),
            "confidence": result.get("confidence", 0.0),
            "reasoning": result.get("reasoning", "No reasoning provided")
        }
        
        # Validate data types
        try:
            if validated["season"] is not None:
                validated["season"] = int(validated["season"])
            if validated["episode"] is not None:
                validated["episode"] = int(validated["episode"])
            validated["confidence"] = float(validated["confidence"])
        except (ValueError, TypeError):
            logger.warning(f"services/llm_service.py::_validate_and_clean_result - Invalid data types in LLM response, using fallback")
            return self._fallback_parse(original_filename)
        
        # Validate confidence range
        validated["confidence"] = max(0.0, min(1.0, validated["confidence"]))
        
        # If show name is empty, use fallback
        if not validated["show_name"]:
            logger.warning(f"services/llm_service.py::_validate_and_clean_result - Empty show name from LLM, using fallback")
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
        logger.info(f"services/llm_service.py::_fallback_parse - Using fallback parsing for: {filename}")
        
        # Use a simple regex fallback
        base = re.sub(r"\.[a-z0-9]{2,4}$", "", filename, flags=re.IGNORECASE)
        cleaned = re.sub(r"[\[\(].*?[\]\)]", "", base)
        cleaned = re.sub(r"[_.]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        # Simple pattern matching
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

    def batch_parse_filenames(self, filenames: list, max_tokens: int = 150) -> list:
        """
        Parse multiple filenames in batch.
        
        Args:
            filenames: List of filenames to parse
            max_tokens: Maximum tokens per response
            
        Returns:
            list: List of parsing results
        """
        logger.info(f"services/llm_service.py::batch_parse_filenames - Parsing {len(filenames)} filenames")
        
        results = []
        for filename in filenames:
            result = self.parse_filename(filename, max_tokens)
            results.append({
                "filename": filename,
                "parsed": result
            })
        
        return results 