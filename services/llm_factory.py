import logging
from services.llm_implementations.llm_interface import LLMInterface
from services.llm_implementations.ollama_implementation import OllamaLLMService
from services.llm_implementations.openai_implementation import OpenAILLMService

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
    llm_type = config.get('llm', 'service', fallback='ollama').lower()
    logger.info(f"llm_factory.py::create_llm_service - Selected LLM service: {llm_type}")

    if llm_type == 'ollama':
        return OllamaLLMService(config)
    elif llm_type == 'openai':
        return OpenAILLMService(config)
    else:
        logger.error(f"llm_factory.py::create_llm_service - Unsupported LLM service: {llm_type}")
        raise ValueError(f"Unsupported LLM service: {llm_type}") 