"""
This module is responsible for instantiating the appropriate LLM service based on the configuration.

The factory is deliberately kept lightweight and does not perform any validation on the LLM service type.
The validation is performed in the individual LLM service implementation's __init__ method.  The reasoning
for this is to isolate the validation logic to the individual LLM service implementation, as each
implementation mwill have different validation requirements, especially as the complexity of the LLM
capability of this service increases.
"""

import logging
from services.llm_implementations.llm_interface import LLMInterface
from services.llm_implementations.ollama_implementation import OllamaLLMService
from services.llm_implementations.openai_implementation import OpenAILLMService
from services.llm_implementations.anthropic_implementation import AnthropicLLMService

logger = logging.getLogger(__name__)

def create_llm_service(config) -> LLMInterface:
    """
    Create and return the appropriate LLM service based on configuration.
    Args:
        config: Loaded configuration object
    Returns:
        LLMInterface: An instance of the appropriate LLM service
    Raises:
        ValueError: If the LLM service type is not supported
    """
    llm_type = config.get('llm', 'service', fallback='ollama').strip().lower()
    logger.info(f"llm_factory.py::create_llm_service - Selected LLM service: {llm_type}")

    if llm_type == 'ollama':
        return OllamaLLMService(config)
    elif llm_type == 'openai':
        return OpenAILLMService(config)
    elif llm_type == 'anthropic':
        return AnthropicLLMService(config)
    else:
        logger.error(f"llm_factory.py::create_llm_service - Unsupported LLM service: {llm_type}")
        raise ValueError(f"Unsupported LLM service: {llm_type}") 