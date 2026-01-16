"""
Prompt management utilities for LangChain-based LLM service.

This module provides utilities for loading and managing prompt templates
from external files. It supports graceful error handling, file reloading
for development environments, and maintains backward compatibility with
existing prompt content and formatting.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.prompts.prompt import PromptTemplate

logger = logging.getLogger(__name__)

# Default prompt directory - will be migrated from existing location
PROMPT_DIR = Path(__file__).parent / "prompts"

# Cache for loaded prompts to avoid repeated file I/O
_prompt_cache: Dict[str, str] = {}


def load_prompt_template(prompt_name: str, use_cache: bool = True) -> str:
    """
    Load prompt content from services/llm/prompts/ directory.
    
    This function loads prompt templates from external files with graceful
    error handling and optional caching for performance. It maintains
    backward compatibility with existing prompt file formats.
    
    Args:
        prompt_name: Name of the prompt file (without .txt extension)
        use_cache: Whether to use cached prompt content (default: True)
        
    Returns:
        str: Prompt template content
        
    Raises:
        FileNotFoundError: If prompt file does not exist
        IOError: If file cannot be read
        
    Examples:
        >>> content = load_prompt_template("parse_filename")
        >>> # Returns content of services/llm/prompts/parse_filename.txt
        
        >>> content = load_prompt_template("select_show_name", use_cache=False)
        >>> # Reloads from file, bypassing cache
    """
    # Check cache first if enabled
    if use_cache and prompt_name in _prompt_cache:
        logger.debug(f"Loading prompt '{prompt_name}' from cache")
        return _prompt_cache[prompt_name]
    
    # Construct file path
    prompt_path = PROMPT_DIR / f"{prompt_name}.txt"
    
    logger.debug(f"Loading prompt template from: {prompt_path}")
    
    try:
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}. "
                f"Available prompts: {list_available_prompts()}"
            )
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if not content.strip():
            logger.warning(f"Prompt file '{prompt_name}' is empty")
        
        # Cache the content
        _prompt_cache[prompt_name] = content
        
        logger.info(f"Successfully loaded prompt template: {prompt_name}")
        return content
        
    except IOError as e:
        logger.error(f"Failed to read prompt file '{prompt_name}': {e}")
        raise IOError(f"Cannot read prompt file '{prompt_name}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading prompt '{prompt_name}': {e}")
        raise


def create_chat_prompt_template(
    prompt_name: str, 
    input_variables: List[str],
    use_cache: bool = True
) -> ChatPromptTemplate:
    """
    Create ChatPromptTemplate from external prompt file.
    
    This function loads prompt content from external files and creates
    LangChain ChatPromptTemplate instances. It handles variable substitution
    and maintains compatibility with existing prompt structures.
    
    Args:
        prompt_name: Name of the prompt file (without .txt extension)
        input_variables: List of variable names expected in the prompt
        use_cache: Whether to use cached prompt content (default: True)
        
    Returns:
        ChatPromptTemplate: Configured prompt template ready for use in chains
        
    Raises:
        FileNotFoundError: If prompt file does not exist
        ValueError: If prompt content is invalid or missing required variables
        
    Examples:
        >>> template = create_chat_prompt_template(
        ...     "parse_filename", 
        ...     ["filename", "format_instructions"]
        ... )
        >>> # Ready to use in LangChain chains
        
        >>> template = create_chat_prompt_template(
        ...     "select_show_name",
        ...     ["show_name", "candidates", "format_instructions"]
        ... )
    """
    logger.debug(f"Creating ChatPromptTemplate for: {prompt_name}")
    
    try:
        # Load prompt content
        prompt_content = load_prompt_template(prompt_name, use_cache)
        
        # Validate that all required variables are present in the prompt
        missing_vars = []
        for var in input_variables:
            if f"{{{var}}}" not in prompt_content:
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(
                f"Prompt '{prompt_name}' missing expected variables: {missing_vars}. "
                f"This may cause runtime errors if these variables are used."
            )
        
        # Create PromptTemplate first
        prompt_template = PromptTemplate(
            template=prompt_content,
            input_variables=input_variables
        )
        
        # Create ChatPromptTemplate with human message
        chat_template = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate(prompt=prompt_template)
        ])
        
        logger.info(f"Successfully created ChatPromptTemplate for: {prompt_name}")
        return chat_template
        
    except Exception as e:
        logger.error(f"Failed to create ChatPromptTemplate for '{prompt_name}': {e}")
        raise ValueError(f"Cannot create prompt template for '{prompt_name}': {e}")


def create_chat_prompt_from_files(
    system_prompt_name: str,
    user_prompt_name: str,
    input_variables: List[str],
    use_cache: bool = True
) -> ChatPromptTemplate:
    """
    Create ChatPromptTemplate from separate system and user prompt files.
    
    This function loads system and user prompts from separate files and creates
    a ChatPromptTemplate with proper message role separation. This pattern is
    optimized for JSON-structured output models that benefit from clear system
    instructions and focused user messages.
    
    Args:
        system_prompt_name: Name of the system prompt file (without .txt extension)
        user_prompt_name: Name of the user prompt file (without .txt extension)
        input_variables: List of variable names expected in the prompts
        use_cache: Whether to use cached prompt content (default: True)
        
    Returns:
        ChatPromptTemplate: Configured prompt template with system and user messages
        
    Raises:
        FileNotFoundError: If either prompt file does not exist
        ValueError: If prompt content is invalid or missing required variables
        
    Examples:
        >>> template = create_chat_prompt_from_files(
        ...     "system_parse_filename_v1",
        ...     "user_parse_filename_v1",
        ...     ["filename"]
        ... )
        >>> # Creates template with separate system and user messages
        
        >>> template = create_chat_prompt_from_files(
        ...     "system_select_show_v1",
        ...     "user_select_show_v1",
        ...     ["show_name", "candidates"]
        ... )
    """
    logger.debug(
        f"Creating ChatPromptTemplate from system='{system_prompt_name}' "
        f"and user='{user_prompt_name}'"
    )
    
    try:
        # Load both prompt contents
        system_content = load_prompt_template(system_prompt_name, use_cache)
        user_content = load_prompt_template(user_prompt_name, use_cache)
        
        # Validate that required variables are present across both prompts
        combined_content = system_content + user_content
        missing_vars = []
        for var in input_variables:
            if f"{{{var}}}" not in combined_content:
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(
                f"Prompts '{system_prompt_name}' and '{user_prompt_name}' "
                f"missing expected variables: {missing_vars}. "
                f"This may cause runtime errors if these variables are used."
            )
        
        # Create ChatPromptTemplate with system and user messages
        chat_template = ChatPromptTemplate.from_messages([
            ("system", system_content),
            ("user", user_content)
        ])
        
        logger.info(
            f"Successfully created ChatPromptTemplate from "
            f"system='{system_prompt_name}' and user='{user_prompt_name}'"
        )
        return chat_template
        
    except Exception as e:
        logger.error(
            f"Failed to create ChatPromptTemplate from "
            f"system='{system_prompt_name}' and user='{user_prompt_name}': {e}"
        )
        raise ValueError(
            f"Cannot create prompt template from "
            f"system='{system_prompt_name}' and user='{user_prompt_name}': {e}"
        )


def list_available_prompts() -> List[str]:
    """
    List all available prompt files in the prompts directory.
    
    Returns:
        List[str]: List of available prompt names (without .txt extension)
        
    Examples:
        >>> prompts = list_available_prompts()
        >>> print(prompts)
        ['parse_filename', 'select_show_name', 'suggest_short_dirname', 'suggest_short_filename']
    """
    try:
        if not PROMPT_DIR.exists():
            logger.warning(f"Prompts directory does not exist: {PROMPT_DIR}")
            return []
        
        prompt_files = []
        for file_path in PROMPT_DIR.glob("*.txt"):
            prompt_name = file_path.stem
            prompt_files.append(prompt_name)
        
        logger.debug(f"Found {len(prompt_files)} prompt files: {prompt_files}")
        return sorted(prompt_files)
        
    except Exception as e:
        logger.error(f"Failed to list available prompts: {e}")
        return []


def clear_prompt_cache() -> None:
    """
    Clear the prompt cache to force reloading from files.
    
    This function is useful during development when prompt files are
    being modified and you want to reload the latest content.
    
    Examples:
        >>> clear_prompt_cache()
        >>> # Next load_prompt_template() call will read from file
    """
    global _prompt_cache
    _prompt_cache.clear()
    logger.debug("Prompt cache cleared")


def validate_prompt_file(prompt_name: str) -> bool:
    """
    Validate that a prompt file exists and is readable.
    
    Args:
        prompt_name: Name of the prompt file to validate
        
    Returns:
        bool: True if prompt file is valid and readable
        
    Examples:
        >>> if validate_prompt_file("parse_filename"):
        ...     print("Prompt file is valid")
    """
    try:
        content = load_prompt_template(prompt_name, use_cache=False)
        return bool(content.strip())
    except Exception as e:
        logger.debug(f"Prompt validation failed for '{prompt_name}': {e}")
        return False


def get_prompt_info(prompt_name: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a prompt file including size and variables.
    
    Args:
        prompt_name: Name of the prompt file
        
    Returns:
        Optional[Dict[str, Any]]: Prompt information or None if file doesn't exist
        
    Examples:
        >>> info = get_prompt_info("parse_filename")
        >>> print(f"Size: {info['size']} bytes, Variables: {info['variables']}")
    """
    try:
        prompt_path = PROMPT_DIR / f"{prompt_name}.txt"
        
        if not prompt_path.exists():
            return None
        
        content = load_prompt_template(prompt_name, use_cache=False)
        
        # Extract variables (simple regex-based approach)
        import re
        variables = re.findall(r'\{([^}]+)\}', content)
        unique_variables = sorted(set(variables))
        
        return {
            "name": prompt_name,
            "path": str(prompt_path),
            "size": len(content),
            "lines": len(content.splitlines()),
            "variables": unique_variables,
            "exists": True
        }
        
    except Exception as e:
        logger.error(f"Failed to get prompt info for '{prompt_name}': {e}")
        return None


def ensure_prompts_directory() -> bool:
    """
    Ensure the prompts directory exists, creating it if necessary.
    
    Returns:
        bool: True if directory exists or was created successfully
    """
    try:
        PROMPT_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Prompts directory ensured: {PROMPT_DIR}")
        return True
    except Exception as e:
        logger.error(f"Failed to create prompts directory: {e}")
        return False