import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class LLMInterface(ABC):
    """
    Abstract base class defining the interface for LLM-based filename parsing services.
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