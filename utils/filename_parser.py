"""
Filename parsing utilities for extracting show metadata from filenames.
Supports both LLM-based and regex-based parsing methods for use in Sync2NAS.
Uses context-based dependency injection for LLM chain service.
"""
import logging
from typing import Optional
from services.llm.schemas import ParsedFilename

logger = logging.getLogger(__name__)

def parse_filename(filename: str, llm_chains=None, llm_confidence_threshold: float = 0.7) -> dict:
    """
    Extract show metadata from a filename using LLM chains or fallback to regex.

    Args:
        filename (str): Raw filename (e.g., "Show.Name.S01E01.1080p.mkv").
        llm_chains: LLM chain service instance (from context).
        llm_confidence_threshold (float): Minimum confidence to accept LLM result.

    Returns:
        dict: Parsed metadata with keys: show_name, season, episode, confidence, reasoning.
    """
    logger.debug(f"Parsing filename: {filename}")

    # Try LangChain parsing first if service is available
    if llm_chains:
        try:
            chain_result: ParsedFilename = llm_chains.parse_filename(filename)
            logger.debug(f"LangChain result: {chain_result}")
            
            # Convert Pydantic model to dict for backward compatibility
            result_dict = chain_result.model_dump()
            
            # If LLM confidence is high enough, use it
            if result_dict.get("confidence", 0.0) >= llm_confidence_threshold:
                logger.info(f"Using LangChain parsing (confidence: {result_dict['confidence']})")
                return result_dict
            else:
                logger.info(f"LangChain confidence too low ({result_dict['confidence']}), falling back to regex")
        except Exception as e:
            logger.exception(f"LangChain parsing failed: {e}, falling back to regex")
    else:
        logger.debug("No LLM chains service available, using regex parsing")

    # Fallback to original regex parsing
    logger.debug(f"Using regex fallback parsing")
    return _regex_parse_filename(filename)


def _regex_parse_filename(filename: str) -> dict:
    """
    Original regex-based filename parsing (fallback method).

    Args:
        filename (str): Raw filename.

    Returns:
        dict: Parsed metadata with confidence and reasoning.
    """
    import re
    
    # Extract CRC32 hash before removing brackets
    crc32_match = re.search(r'\[([0-9A-Fa-f]{8})\]', filename)
    crc32 = crc32_match.group(1).upper() if crc32_match else None
    
    # Remove file extension
    base = re.sub(r"\.[a-z0-9]{2,4}$", "", filename, flags=re.IGNORECASE)

    # Remove all [tags] and (metadata)
    cleaned = re.sub(r"[\[\(].*?[\]\)]", "", base)

    # Normalize delimiters
    cleaned = re.sub(r"[_.]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Patterns to match the show name, season, and episode
    patterns = [
        r"(?P<name>.*?)[\s\-]+(?P<season>\d{1,2})(?:st|nd|rd|th)?[\s\-]+Season[\s\-]+(?P<episode>\d{1,3})",
        r"(?P<name>.*?)[\s\-]+[Ss](?P<season>\d{1,2})[Ee](?P<episode>\d{1,3})",
        r"(?P<name>.*?)[\s\-]+[Ss](?P<season>\d{1,2})[\s\-]+(?P<episode>\d{1,3})",
        r"(?P<name>.*?)(?:[\s\-]+[Ss](?P<season>\d{1,2}).*)?[\s\-]+[Ee](?P<episode>\d{1,3})",
        r"(?P<name>.*?)[\s\-]+(?P<episode>\d{1,3})(?:v\d)?\b",
        r"(?P<name>.*?)[\s\-]+(?P<episode>\d{1,3})$",
        r"(?P<name>.*?)\s+[Ss](?P<season>\d{1,2})[Ee](?P<episode>\d{1,3})"
    ]

    for index, pattern in enumerate(patterns):
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            groups = match.groupdict()
            show_name = groups.get("name", "").strip(" -_")
            season = int(groups["season"]) if groups.get("season") else None
            episode = int(groups["episode"]) if groups.get("episode") else None
            logger.debug(f"Parsed: Show={show_name}, Season={season}, Episode={episode}, CRC32={crc32} - Pattern {index}")
            return {
                "show_name": show_name, 
                "season": season, 
                "episode": episode,
                "crc32": crc32,
                "confidence": 0.6,
                "reasoning": f"Regex pattern {index} matched"
            }

    logger.debug(f"No match found; fallback name: {cleaned}, CRC32={crc32}")
    return {
        "show_name": cleaned, 
        "season": None, 
        "episode": None,
        "crc32": crc32,
        "confidence": 0.1,
        "reasoning": "No regex pattern matched"
    } 