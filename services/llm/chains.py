"""
LangChain chains implementation using LCEL composition.

This module implements LangChain chains for:
- Filename parsing with structured output
- Batch filename processing with parallel execution
- Short name suggestions for directories and files
- TMDB show matching with confidence scoring

All chains use LCEL (LangChain Expression Language) for composable,
testable chain construction while maintaining backward compatibility
with existing functionality.
"""

import json
import logging
from typing import List, Dict, Any, Optional

from langchain_core.runnables import Runnable, RunnablePassthrough, RunnableLambda
from langchain_core.language_models.base import BaseLanguageModel

from .schemas import ParsedFilename, ShortName, ShowMatch
from .prompts import create_chat_prompt_template

logger = logging.getLogger(__name__)

# Note: Global singletons removed - chains are now managed by LLMChainService
# This module provides factory functions for creating chain instances


def create_filename_parser(llm: BaseLanguageModel) -> Runnable:
    """
    Create LCEL chain for filename parsing using native structured output.
    
    This function creates a LangChain chain that parses TV show filenames
    using system and user prompts with LangChain's native structured output
    capabilities. The chain uses JSON-optimized models that directly return
    validated Pydantic objects without requiring response cleaning or field
    translation.
    
    Args:
        llm: LangChain LLM instance to use for parsing
    
    Returns:
        Runnable: LCEL chain for filename parsing
        
    Examples:
        >>> parser = create_filename_parser(llm_instance)
        >>> result = parser.invoke({"filename": "Attack on Titan S01E05.mkv"})
        >>> print(result.show_name, result.season, result.episode)
        Attack on Titan 1 5
    """
    logger.debug("Creating filename parsing chain with native structured output")
    
    # Load system and user prompts separately
    from .prompts import create_chat_prompt_from_files
    
    prompt = create_chat_prompt_from_files(
        system_prompt_name="system_parse_filename_v1",
        user_prompt_name="user_parse_filename_v1",
        input_variables=["filename"]
    )
    
    # Create structured LLM that returns ParsedFilename objects directly
    structured_llm = llm.with_structured_output(ParsedFilename)
    
    # Create simple LCEL chain: prompt | structured_llm
    chain = prompt | structured_llm
    
    logger.info("Filename parsing chain created successfully with native structured output")
    return chain


def create_batch_filename_parser(llm: BaseLanguageModel) -> Runnable:
    """
    Create chain for parallel batch filename parsing.
    
    This function creates a chain that processes multiple filenames in parallel
    using the single filename parser with controlled concurrency to avoid
    overwhelming the LLM service.
    
    Args:
        llm: LangChain LLM instance to use for parsing
    
    Returns:
        Runnable: LCEL chain for batch filename parsing
        
    Examples:
        >>> batch_parser = create_batch_filename_parser(llm_instance)
        >>> filenames = ["Show1 S01E01.mkv", "Show2 S02E03.mkv"]
        >>> results = batch_parser.invoke(filenames)
        >>> print(len(results))  # Should be 2
    """
    logger.debug("Creating batch filename parsing chain")
    
    # Get single filename parser with passed LLM instance
    single_parser = create_filename_parser(llm)
    
    def batch_process(filenames: List[str]) -> List[ParsedFilename]:
        """Process multiple filenames with controlled concurrency."""
        if not filenames:
            return []
        
        logger.info(f"Processing batch of {len(filenames)} filenames")
        
        # Create inputs for batch processing
        inputs = [{"filename": filename} for filename in filenames]
        
        # Use batch processing with max_concurrency of 5
        try:
            results = single_parser.batch(inputs, config={"max_concurrency": 5})
            logger.info(f"Successfully processed {len(results)} filenames in batch")
            return results
        except Exception as e:
            logger.error(f"Batch processing failed with error: {e}", exc_info=True)
            # Fallback to sequential processing
            logger.warning("Falling back to sequential processing due to batch error")
            results = []
            for input_data in inputs:
                try:
                    result = single_parser.invoke(input_data)
                    results.append(result)
                except Exception as seq_e:
                    logger.error(
                        f"Sequential processing failed for '{input_data['filename']}': {seq_e}",
                        exc_info=True
                    )
                    # Create fallback result with low confidence
                    fallback_result = ParsedFilename(
                        show_name=input_data['filename'],
                        season=None,
                        episode=None,
                        crc32=None,
                        confidence=0.1,
                        reasoning=f"Fallback result due to parsing error: {str(seq_e)}"
                    )
                    results.append(fallback_result)
            return results
    
    # Wrap in RunnableLambda
    chain = RunnableLambda(batch_process)
    
    logger.info("Batch filename parsing chain created successfully")
    return chain


def create_short_name_suggester(name_type: str, llm: BaseLanguageModel) -> Runnable:
    """
    Create chain for short name suggestions with character restrictions.
    
    This function creates a chain that suggests shortened names for directories
    or filenames using existing prompt templates and character validation.
    
    Args:
        name_type: Type of name to suggest ("directory" or "filename")
        llm: LangChain LLM instance to use for suggestions
        
    Returns:
        Runnable: LCEL chain for short name suggestions
        
    Examples:
        >>> suggester = create_short_name_suggester("directory", llm_instance)
        >>> result = suggester.invoke({
        ...     "long_name": "Attack on Titan Season 1",
        ...     "max_length": 20
        ... })
        >>> print(result)  # Returns string like "AoT_S1"
    """
    logger.debug(f"Creating short name suggester chain for {name_type}")
    
    # Validate name_type
    if name_type not in ["directory", "filename"]:
        raise ValueError(f"Invalid name_type: {name_type}. Must be 'directory' or 'filename'")
    
    # Load appropriate prompt template
    if name_type == "directory":
        prompt_name = "suggest_short_dirname"
    elif name_type == "filename":
        prompt_name = "suggest_short_filename"
    else:
        raise ValueError(f"Invalid name_type: {name_type}. Must be 'directory' or 'filename'")
    
    prompt = create_chat_prompt_template(prompt_name, ["long_name", "max_length"])
    
    # Use passed LLM instance
    
    # Use modern with_structured_output() method
    structured_llm = llm.with_structured_output(ShortName)
    
    # Create LCEL chain with structured output
    chain = (
        prompt
        | structured_llm
        | RunnableLambda(lambda x: x.short_name)  # Extract string value
    )
    
    logger.info(f"Short name suggester chain created successfully for {name_type}")
    return chain


def create_show_matcher(llm: BaseLanguageModel) -> Runnable:
    """
    Create chain for TMDB show matching with candidate formatting.
    
    This function creates a chain that matches show names to TMDB candidates
    using existing prompt templates and candidate preprocessing logic.
    
    Args:
        llm: LangChain LLM instance to use for matching
    
    Returns:
        Runnable: LCEL chain for show matching
        
    Examples:
        >>> matcher = create_show_matcher(llm_instance)
        >>> candidates = [{"tmdb_id": 1429, "name": "Attack on Titan", ...}]
        >>> result = matcher.invoke({
        ...     "show_name": "Shingeki no Kyojin",
        ...     "candidates": candidates
        ... })
        >>> print(result.tmdb_id, result.show_name)
        1429 Attack on Titan
    """
    logger.debug("Creating show matching chain")
    
    # Load prompt template
    prompt = create_chat_prompt_template("select_show_name", ["show_name", "candidates"])
    
    # Use passed LLM instance
    
    # Use modern with_structured_output() method
    structured_llm = llm.with_structured_output(ShowMatch)
    
    def format_candidates(inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Format TMDB candidates for LLM processing."""
        candidates = inputs.get("candidates", [])
        
        if not candidates:
            logger.warning("No candidates provided for show matching")
            return {**inputs, "candidates": "[]"}
        
        logger.debug(f"Formatting {len(candidates)} candidates for LLM")
        
        formatted = []
        for candidate in candidates:
            # Extract and format candidate information
            formatted_candidate = {
                "tmdb_id": candidate.get("tmdb_id", 0),
                "name": candidate.get("name", ""),
                "original_name": candidate.get("original_name", ""),
                "first_air_date": candidate.get("first_air_date", ""),
                "overview": (candidate.get("overview", "") or "")[:200]  # Truncate to 200 chars
            }
            formatted.append(formatted_candidate)
        
        # Convert to JSON string for prompt
        candidates_json = json.dumps(formatted, indent=2, ensure_ascii=False)
        
        return {**inputs, "candidates": candidates_json}
    
    # Create LCEL chain with candidate formatting and structured output
    chain = (
        RunnableLambda(format_candidates)
        | prompt
        | structured_llm
    )
    
    logger.info("Show matching chain created successfully")
    return chain


# Factory functions for creating chain instances
# These are used by LLMChainService for dependency injection
