import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class LLMInterface(ABC):
    """
    Abstract base class defining the interface for LLM-based filename parsing services.

    All subclasses must implement methods for parsing filenames, batch parsing, and suggesting short directory/filenames.

    Methods:
        parse_filename(filename, max_tokens): Parse a filename using the LLM.
        batch_parse_filenames(filenames, max_tokens): Parse multiple filenames in batch.
        suggest_short_dirname(long_name, max_length): Suggest a short directory name.
        suggest_short_filename(long_name, max_length): Suggest a short filename.
    """

    @abstractmethod
    def parse_filename(self, filename: str, max_tokens: int = 150) -> Dict[str, Any]:
        """
        Parse a filename using the LLM to extract show metadata.
        Args:
            filename: Raw filename to parse
            max_tokens: Maximum tokens for LLM response
        Returns:
            dict: Parsed metadata
        """
        pass

    @abstractmethod
    def batch_parse_filenames(self, filenames: List[str], max_tokens: int = 150) -> List[Dict[str, Any]]:
        """
        Parse multiple filenames in batch.
        Args:
            filenames: List of filenames to parse
            max_tokens: Maximum tokens per response
        Returns:
            list: List of parsing results
        """
        pass

    @abstractmethod
    def suggest_short_dirname(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable directory name for a given long name using the LLM.
        Args:
            long_name: The original long directory name
            max_length: The maximum allowed length for the short name
        Returns:
            str: Suggested short directory name
        """
        pass 
    
    @abstractmethod
    def suggest_short_filename(self, long_name: str, max_length: int = 20) -> str:
        """
        Suggest a short, human-readable filename for a given long name using the LLM.
        Args:
            long_name: The original long filename
            max_length: The maximum allowed length for the short name
        Returns:
            str: Suggested short filename
        """
        pass

    @abstractmethod
    def suggest_show_name(self, show_name: str, detailed_results: list) -> dict:
        """
        Suggest the best show match and English name from TMDB results using the LLM.
        
        Args:
            show_name: The original show name to match
            detailed_results: List of detailed TMDB results to choose from
            
        Returns:
            dict: Dictionary with keys 'tmdb_id', 'show_name', and optionally 'confidence', 'reasoning'
        """
        pass