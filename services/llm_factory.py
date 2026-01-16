"""
LLM Factory Service for Sync2NAS.

This module provides a factory for creating LLM service instances based on configuration,
following the same pattern as other services (database, SFTP, TMDB).
Replaces the singleton pattern with proper dependency injection.
"""

import logging
from typing import Dict, Any, Optional

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

from utils.sync2nas_config import (
    get_config_value,
    get_config_bool,
    get_config_string,
    has_config_section
)

logger = logging.getLogger(__name__)


def create_llm_service(config: Dict[str, Any]) -> BaseLanguageModel:
    """
    Create LangChain LLM instance using Sync2NAS configuration patterns.
    
    This function creates appropriate LangChain LLM instances based on the configured
    service type, following the same factory pattern as other services in the project.
    
    Args:
        config: Configuration dictionary from load_configuration()
        
    Returns:
        BaseLanguageModel: Configured LangChain LLM instance
        
    Raises:
        ValueError: If LLM service is not configured or unsupported
        ImportError: If required LangChain provider package is not installed
        Exception: If LLM instance creation fails
        
    Examples:
        >>> config = load_configuration("config/sync2nas_config.ini")
        >>> llm = create_llm_service(config)
        >>> # LLM instance ready for use with LangChain chains
    """
    logger.debug("Creating LLM instance from configuration")
    
    # Get LLM service type using existing configuration patterns
    llm_service = get_config_string(config, "llm", "service", "").lower()
    
    if not llm_service:
        raise ValueError(
            "LLM service not configured. Please set [llm] service in configuration file "
            "or use SYNC2NAS_LLM_SERVICE environment variable. "
            "Supported services: anthropic, openai, ollama"
        )
    
    logger.info(f"Creating LLM instance for service: {llm_service}")
    
    try:
        if llm_service == "anthropic":
            return _create_anthropic_llm(config)
        elif llm_service == "openai":
            return _create_openai_llm(config)
        elif llm_service == "ollama":
            return _create_ollama_llm(config)
        else:
            raise ValueError(
                f"Unsupported LLM service: {llm_service}. "
                f"Supported services: anthropic, openai, ollama"
            )
    except ImportError as e:
        raise ImportError(
            f"Failed to import LangChain provider for {llm_service}. "
            f"Please install the required package: pip install langchain-{llm_service}. "
            f"Original error: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to create LLM instance for {llm_service}: {e}")
        raise Exception(f"LLM instance creation failed: {e}")


def _create_anthropic_llm(config: Dict[str, Any]) -> BaseLanguageModel:
    """
    Create Anthropic LLM instance from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        BaseLanguageModel: Configured Anthropic LLM instance
    """
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "Anthropic LangChain integration not available. "
            "Install with: pip install langchain-anthropic"
        )
    
    # Get Anthropic configuration
    api_key = get_config_string(config, "anthropic", "api_key", "")
    model = get_config_string(config, "anthropic", "model", "claude-3-haiku-20240307")
    max_tokens = int(get_config_string(config, "anthropic", "max_tokens", "1000"))
    temperature = float(get_config_string(config, "anthropic", "temperature", "0.1"))
    
    if not api_key:
        raise ValueError(
            "Anthropic API key not configured. Please set api_key in [anthropic] section "
            "or use SYNC2NAS_ANTHROPIC_API_KEY environment variable."
        )
    
    logger.debug(f"Creating ChatAnthropic with model: {model}, max_tokens: {max_tokens}, temperature: {temperature}")
    
    return ChatAnthropic(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )


def _create_openai_llm(config: Dict[str, Any]) -> BaseLanguageModel:
    """
    Create OpenAI LLM instance from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        BaseLanguageModel: Configured OpenAI LLM instance
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "OpenAI LangChain integration not available. "
            "Install with: pip install langchain-openai"
        )
    
    # Get OpenAI configuration
    api_key = get_config_string(config, "openai", "api_key", "")
    model = get_config_string(config, "openai", "model", "gpt-3.5-turbo")
    max_tokens = int(get_config_string(config, "openai", "max_tokens", "1000"))
    temperature = float(get_config_string(config, "openai", "temperature", "0.1"))
    
    if not api_key:
        raise ValueError(
            "OpenAI API key not configured. Please set api_key in [openai] section "
            "or use SYNC2NAS_OPENAI_API_KEY environment variable."
        )
    
    logger.debug(f"Creating ChatOpenAI with model: {model}, max_tokens: {max_tokens}, temperature: {temperature}")
    
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )


def _create_ollama_llm(config: Dict[str, Any]) -> BaseLanguageModel:
    """
    Create Ollama LLM instance from configuration.
    
    Uses ChatOllama for better structured output support with JSON-optimized models.
    Validates model compatibility and logs warnings for non-JSON-optimized models.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        BaseLanguageModel: Configured Ollama LLM instance
    """
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError(
            "Ollama LangChain integration not available. "
            "Install with: pip install langchain-ollama"
        )
    
    # Get Ollama configuration using existing utilities
    host = get_config_string(config, "ollama", "host", "http://localhost:11434")
    model = get_config_string(config, "ollama", "model", "ministral-3:8b")
    temperature = float(get_config_string(config, "ollama", "temperature", "1.0"))
    
    # Validate model for JSON output compatibility
    json_optimized_models = [
        'ministral-3:8b',
        'ministral-3:14b'
        'qwen2.5:7b',
        'llama3.2:3b',
        'qwen2.5',
        'ministral',
        'llama3.2'
    ]
    
    # Check if model is JSON-optimized (exact match or prefix match)
    is_json_optimized = any(
        model == json_model or model.startswith(json_model.split(':')[0])
        for json_model in json_optimized_models
    )
    
    if not is_json_optimized:
        logger.warning(
            f"Model '{model}' may not be optimized for JSON structured output. "
            f"Recommended models for best results: {', '.join(json_optimized_models[:3])}. "
            f"You may experience parsing issues with non-JSON-optimized models."
        )
    
    logger.debug(f"Creating ChatOllama with host: {host}, model: {model}, temperature: {temperature}")
    
    return ChatOllama(
        base_url=host,
        model=model,
        temperature=temperature
    )


def setup_llm_caching_and_tracing(config: Dict[str, Any]) -> None:
    """
    Configure LangChain caching and optional LangSmith tracing from configuration.
    
    This function sets up optional caching and tracing features using the existing
    configuration system. LangSmith tracing is only enabled if the langsmith package
    is available and properly configured.
    
    Args:
        config: Configuration dictionary from load_configuration()
        
    Examples:
        >>> config = load_configuration("config/sync2nas_config.ini")
        >>> setup_llm_caching_and_tracing(config)
        >>> # Caching and tracing now configured based on config settings
    """
    import os
    
    logger.debug("Setting up LangChain caching and tracing")
    
    # Setup caching if enabled
    enable_cache = get_config_bool(config, "llm", "enable_cache", False)
    if enable_cache:
        cache_path = get_config_string(config, "llm", "cache_path", ".langchain_cache.db")
        logger.info(f"Enabling LangChain SQLite cache at: {cache_path}")
        
        try:
            cache = SQLiteCache(database_path=cache_path)
            set_llm_cache(cache)
            logger.info("LangChain caching enabled successfully")
        except Exception as e:
            logger.warning(f"Failed to enable LangChain caching: {e}")
    else:
        logger.debug("LangChain caching disabled")
    
    # Setup tracing if enabled and available
    enable_tracing = get_config_bool(config, "llm", "enable_tracing", False)
    if enable_tracing:
        try:
            # Check if langsmith is available
            import langsmith
            
            # Get tracing configuration
            api_key = get_config_string(config, "llm", "langsmith_api_key", "")
            project = get_config_string(config, "llm", "langsmith_project", "sync2nas")
            
            if not api_key:
                logger.warning(
                    "LangSmith tracing enabled but no API key configured. "
                    "Please set langsmith_api_key in [llm] section or use SYNC2NAS_LLM_LANGSMITH_API_KEY environment variable."
                )
                return
            
            # Set LangSmith environment variables
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = api_key
            os.environ["LANGCHAIN_PROJECT"] = project
            
            logger.info(f"LangSmith tracing enabled for project: {project}")
            
        except ImportError:
            logger.warning(
                "LangSmith tracing requested but langsmith package not available. "
                "Install with: pip install langsmith"
            )
        except Exception as e:
            logger.warning(f"Failed to setup LangSmith tracing: {e}")
    else:
        logger.debug("LangSmith tracing disabled")


def validate_llm_config(config: Dict[str, Any]) -> None:
    """
    Validate LLM configuration and test connectivity.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
        Exception: If LLM service is not accessible
    """
    logger.debug("Validating LLM configuration")
    
    # Check if LLM section exists
    if not has_config_section(config, "llm"):
        raise ValueError("LLM configuration section [llm] not found")
    
    # Get and validate service type
    llm_service = get_config_string(config, "llm", "service", "").lower()
    if not llm_service:
        raise ValueError("LLM service not specified in [llm] section")
    
    if llm_service not in ["anthropic", "openai", "ollama"]:
        raise ValueError(f"Unsupported LLM service: {llm_service}")
    
    # Validate service-specific configuration
    if llm_service == "anthropic":
        if not has_config_section(config, "anthropic"):
            raise ValueError("Anthropic configuration section [anthropic] not found")
        api_key = get_config_string(config, "anthropic", "api_key", "")
        if not api_key:
            raise ValueError("Anthropic API key not configured")
    
    elif llm_service == "openai":
        if not has_config_section(config, "openai"):
            raise ValueError("OpenAI configuration section [openai] not found")
        api_key = get_config_string(config, "openai", "api_key", "")
        if not api_key:
            raise ValueError("OpenAI API key not configured")
    
    elif llm_service == "ollama":
        if not has_config_section(config, "ollama"):
            raise ValueError("Ollama configuration section [ollama] not found")
    
    # Test LLM connectivity
    try:
        llm = create_llm_service(config)
        # Simple test to verify the LLM is accessible
        test_response = llm.invoke("Test")
        logger.info("✓ LLM service validation successful")
    except Exception as e:
        raise Exception(f"LLM service connectivity test failed: {e}")