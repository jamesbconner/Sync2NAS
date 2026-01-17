"""
LLM Chain Service for context-based dependency injection.

This service encapsulates LangChain chains and provides a clean interface
for filename parsing, batch processing, and other LLM-based operations.
Follows the project's context-based dependency injection pattern.
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.runnables import Runnable

from .llm.chains import (
    create_filename_parser,
    create_batch_filename_parser,
    create_short_name_suggester,
    create_show_matcher
)
from .llm.schemas import ParsedFilename, ShowMatch

logger = logging.getLogger(__name__)


class LLMChainService:
    """
    Service class for managing LangChain chains with caching.
    
    This service follows the project's dependency injection pattern by
    accepting an LLM service instance and managing chain lifecycles
    internally while providing a clean external interface.
    """
    
    def __init__(self, llm_service):
        """
        Initialize the LLM Chain Service.
        
        Args:
            llm_service: The LLM service instance (from context)
        """
        self.llm_service = llm_service
        
        # Cached chain instances (internal singletons)
        self._filename_parser: Optional[Runnable] = None
        self._batch_parser: Optional[Runnable] = None
        self._dirname_suggester: Optional[Runnable] = None
        self._filename_suggester: Optional[Runnable] = None
        self._show_matcher: Optional[Runnable] = None
        
        logger.debug("LLM Chain Service initialized")
    
    def parse_filename(self, filename: str) -> ParsedFilename:
        """
        Parse single filename using cached chain instance.
        
        Args:
            filename: Filename to parse
            
        Returns:
            ParsedFilename: Parsed filename with metadata
            
        Examples:
            >>> result = llm_chains.parse_filename("Attack on Titan S01E05.mkv")
            >>> print(result.show_name, result.season, result.episode)
            Attack on Titan 1 5
        """
        if self._filename_parser is None:
            self._filename_parser = create_filename_parser(self.llm_service)
            logger.debug("Created cached filename parser chain")
        
        logger.debug(f"Parsing filename: {filename}")
        result = self._filename_parser.invoke({"filename": filename})
        logger.info(
            f"Parsed filename '{filename}' -> show='{result.show_name}', "
            f"S{result.season}E{result.episode}, confidence={result.confidence:.2f}"
        )
        return result
    
    def parse_filenames(self, filenames: List[str]) -> List[ParsedFilename]:
        """
        Parse multiple filenames in parallel using cached chain instance.
        
        Args:
            filenames: List of filenames to parse
            
        Returns:
            List[ParsedFilename]: List of parsed filenames with metadata
            
        Examples:
            >>> filenames = ["Show1 S01E01.mkv", "Show2 S02E03.mkv"]
            >>> results = llm_chains.parse_filenames(filenames)
            >>> print(len(results))  # Should be 2
        """
        if self._batch_parser is None:
            self._batch_parser = create_batch_filename_parser(self.llm_service)
            logger.debug("Created cached batch parser chain")
        
        logger.info(f"Parsing batch of {len(filenames)} filenames")
        results = self._batch_parser.invoke(filenames)
        
        # Log summary of batch results
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0
        logger.info(
            f"Batch parsing complete: {len(results)} files processed, "
            f"avg confidence={avg_confidence:.2f}"
        )
        return results
    
    def suggest_dirname(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest shortened directory name using cached chain instance.
        
        Args:
            long_name: Original long directory name
            max_length: Maximum length for suggested name
            
        Returns:
            str: Suggested short directory name
            
        Examples:
            >>> result = llm_chains.suggest_dirname("Attack on Titan Season 1", 15)
            >>> print(result)  # e.g., "AoT_S1"
        """
        if self._dirname_suggester is None:
            self._dirname_suggester = create_short_name_suggester("directory", self.llm_service)
            logger.debug("Created cached directory name suggester")
        
        logger.debug(f"Suggesting directory name for: {long_name} (max_length: {max_length})")
        return self._dirname_suggester.invoke({"long_name": long_name, "max_length": max_length})
    
    def suggest_filename(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest shortened filename using cached chain instance.
        
        Args:
            long_name: Original long filename
            max_length: Maximum length for suggested name
            
        Returns:
            str: Suggested short filename
            
        Examples:
            >>> result = llm_chains.suggest_filename("Attack on Titan Episode 5", 15)
            >>> print(result)  # e.g., "AoT_E05"
        """
        if self._filename_suggester is None:
            self._filename_suggester = create_short_name_suggester("filename", self.llm_service)
            logger.debug("Created cached filename suggester")
        
        logger.debug(f"Suggesting filename for: {long_name} (max_length: {max_length})")
        return self._filename_suggester.invoke({"long_name": long_name, "max_length": max_length})
    
    def match_show(self, show_name: str, candidates: List[Dict[str, Any]]) -> ShowMatch:
        """
        Match show name to TMDB candidates using cached chain instance.
        
        Args:
            show_name: Show name to match
            candidates: List of TMDB candidate dictionaries
            
        Returns:
            ShowMatch: Best matching show with confidence score
            
        Examples:
            >>> candidates = [{"tmdb_id": 1429, "name": "Attack on Titan", ...}]
            >>> result = llm_chains.match_show("Shingeki no Kyojin", candidates)
            >>> print(result.tmdb_id, result.confidence)
            1429 0.95
        """
        if self._show_matcher is None:
            self._show_matcher = create_show_matcher(self.llm_service)
            logger.debug("Created cached show matcher chain")
        
        logger.debug(f"Matching show '{show_name}' against {len(candidates)} candidates")
        result = self._show_matcher.invoke({"show_name": show_name, "candidates": candidates})
        logger.info(
            f"Matched show '{show_name}' -> '{result.show_name}' "
            f"(tmdb_id={result.tmdb_id}, confidence={result.confidence:.2f})"
        )
        return result
    
    def reset_chains(self) -> None:
        """
        Reset all cached chain instances for testing purposes.
        
        This method clears all cached chain instances, forcing them to be
        recreated on next access. Primarily used for testing.
        """
        self._filename_parser = None
        self._batch_parser = None
        self._dirname_suggester = None
        self._filename_suggester = None
        self._show_matcher = None
        
        logger.debug("All cached chain instances reset")