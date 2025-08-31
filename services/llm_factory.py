"""
This module is responsible for instantiating the appropriate LLM service based on the configuration.

The factory now includes comprehensive configuration validation, normalization, and health checking
to ensure robust service creation and clear error reporting when configuration issues occur.
"""

import logging
import time
from typing import Union, Dict, Any, Optional
from configparser import ConfigParser
from services.llm_implementations.llm_interface import LLMInterface
from services.llm_implementations.ollama_implementation import OllamaLLMService
from services.llm_implementations.openai_implementation import OpenAILLMService
from services.llm_implementations.anthropic_implementation import AnthropicLLMService
from utils.sync2nas_config import get_config_value
from utils.config.config_validator import ConfigValidator
from utils.config.config_normalizer import ConfigNormalizer
from utils.config.health_checker import ConfigHealthChecker
from utils.config.config_monitor import get_config_monitor

logger = logging.getLogger(__name__)

class LLMServiceCreationError(Exception):
    """Exception raised when LLM service creation fails due to configuration issues."""
    
    def __init__(self, message: str, validation_result: Optional[object] = None):
        super().__init__(message)
        self.validation_result = validation_result


def create_llm_service(
    config: Union[ConfigParser, Dict[str, Dict[str, Any]]], 
    validate_health: bool = True,
    startup_mode: bool = False
) -> LLMInterface:
    """
    Create and return the appropriate LLM service based on configuration.
    
    This function now includes comprehensive validation, normalization, and optional
    health checking to ensure robust service creation.

    Args:
        config: Loaded configuration object (ConfigParser or normalized dict).
        validate_health: Whether to perform connectivity health checks (default: True).
        startup_mode: Whether this is called during application startup (affects error handling).

    Returns:
        LLMInterface: An instance of the appropriate LLM service.

    Raises:
        LLMServiceCreationError: If configuration validation fails or service creation fails.
        ValueError: If the LLM service type is not supported (legacy compatibility).
    """
    logger.info("Creating LLM service with validation")
    
    # Initialize validation components and monitoring
    validator = ConfigValidator()
    normalizer = ConfigNormalizer()
    monitor = get_config_monitor()
    
    # Start monitoring configuration loading
    config_operation_id = monitor.log_config_loading_start("llm_factory")
    start_time = time.time()
    
    try:
        # Step 1: Normalize configuration and apply environment overrides
        logger.debug("Normalizing configuration and applying environment overrides")
        normalized_config = normalizer.normalize_and_override(config)
        
        # Count sections loaded
        sections_loaded = len(normalized_config)
        
        # Step 2: Validate configuration
        logger.debug("Validating LLM configuration")
        validation_result = validator.validate_llm_config(normalized_config)
        
        if not validation_result.is_valid:
            error_msg = _format_validation_errors(validation_result)
            logger.error(f"LLM configuration validation failed: {error_msg}")
            
            if startup_mode:
                # In startup mode, provide detailed error reporting and exit
                _handle_startup_validation_failure(validation_result)
            
            raise LLMServiceCreationError(
                f"LLM configuration validation failed: {error_msg}",
                validation_result
            )
        
        # Log any warnings
        if validation_result.warnings:
            for warning in validation_result.warnings:
                logger.warning(f"LLM configuration warning: {warning}")
        
        # Step 3: Get validated service type
        llm_type = normalized_config.get('llm', {}).get('service', 'ollama').strip().lower()
        logger.info(f"Selected LLM service: {llm_type}")
        
        # Step 4: Perform health check if requested
        if validate_health:
            logger.debug(f"Performing health check for {llm_type}")
            health_checker = ConfigHealthChecker()
            
            try:
                health_results = health_checker.check_llm_health_sync(normalized_config)
                
                for health_result in health_results:
                    if not health_result.is_healthy:
                        error_msg = f"Health check failed for {health_result.service}: {health_result.error_message}"
                        logger.error(error_msg)
                        
                        if startup_mode:
                            _handle_startup_health_failure(health_result)
                        
                        raise LLMServiceCreationError(
                            f"LLM service health check failed: {error_msg}",
                            health_result
                        )
                    else:
                        logger.info(f"Health check passed for {health_result.service} "
                                  f"(response time: {health_result.response_time_ms:.1f}ms)")
            
            except Exception as e:
                if isinstance(e, LLMServiceCreationError):
                    raise
                logger.warning(f"Health check failed with exception: {e}")
                if startup_mode:
                    # In startup mode, health check failures are critical
                    raise LLMServiceCreationError(f"Health check failed: {str(e)}")
        
        # Step 5: Create the appropriate service instance
        logger.debug(f"Creating {llm_type} service instance")
        
        service_instance = None
        if llm_type == 'ollama':
            service_instance = OllamaLLMService(normalized_config)
        elif llm_type == 'openai':
            service_instance = OpenAILLMService(normalized_config)
        elif llm_type == 'anthropic':
            service_instance = AnthropicLLMService(normalized_config)
        else:
            error_msg = f"Unsupported LLM service: {llm_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Log successful configuration loading
        duration_ms = (time.time() - start_time) * 1000
        monitor.log_config_loading_complete(
            config_operation_id, 
            success=True, 
            duration_ms=duration_ms,
            sections_loaded=sections_loaded
        )
        
        return service_instance
    
    except Exception as e:
        # Log failed configuration loading
        duration_ms = (time.time() - start_time) * 1000
        monitor.log_config_loading_complete(
            config_operation_id,
            success=False,
            duration_ms=duration_ms,
            sections_loaded=0,
            error_message=str(e)
        )
        
        if isinstance(e, (LLMServiceCreationError, ValueError)):
            raise
        
        # Wrap unexpected exceptions
        logger.exception(f"Unexpected error creating LLM service: {e}")
        raise LLMServiceCreationError(f"Unexpected error creating LLM service: {str(e)}")


def create_llm_service_legacy(config: Union[ConfigParser, Dict[str, Dict[str, Any]]]) -> LLMInterface:
    """
    Legacy function for creating LLM service without validation.
    
    This function maintains backward compatibility for code that expects
    the old behavior without validation.
    
    Args:
        config: Loaded configuration object (ConfigParser or normalized dict).

    Returns:
        LLMInterface: An instance of the appropriate LLM service.

    Raises:
        ValueError: If the LLM service type is not supported.
    """
    logger.warning("Using legacy LLM service creation without validation")
    
    # Get LLM service type with case-insensitive lookup
    llm_type = get_config_value(config, 'llm', 'service', 'ollama').strip().lower()
    logger.info(f"Selected LLM service: {llm_type}")

    if llm_type == 'ollama':
        return OllamaLLMService(config)
    elif llm_type == 'openai':
        return OpenAILLMService(config)
    elif llm_type == 'anthropic':
        return AnthropicLLMService(config)
    else:
        logger.exception(f"Unsupported LLM service: {llm_type}")
        raise ValueError(f"Unsupported LLM service: {llm_type}")


def validate_llm_config_only(config: Union[ConfigParser, Dict[str, Dict[str, Any]]]) -> object:
    """
    Validate LLM configuration without creating a service instance.
    
    Useful for configuration testing and validation-only scenarios.
    
    Args:
        config: Loaded configuration object (ConfigParser or normalized dict).
        
    Returns:
        ValidationResult: Detailed validation results.
    """
    validator = ConfigValidator()
    normalizer = ConfigNormalizer()
    
    normalized_config = normalizer.normalize_and_override(config)
    return validator.validate_llm_config(normalized_config)


def _format_validation_errors(validation_result: object) -> str:
    """Format validation errors into a readable error message."""
    if not validation_result.errors:
        return "Unknown validation error"
    
    error_messages = []
    for error in validation_result.errors:
        if error.key:
            error_messages.append(f"[{error.section}].{error.key}: {error.message}")
        else:
            error_messages.append(f"[{error.section}]: {error.message}")
    
    return "; ".join(error_messages)


def _handle_startup_validation_failure(validation_result: object) -> None:
    """Handle validation failures during application startup."""
    print("\n❌ LLM Configuration Validation Failed")
    print("=" * 50)
    
    print("\nErrors found:")
    for i, error in enumerate(validation_result.errors, 1):
        print(f"{i}. {error.message}")
        if error.suggestion:
            print(f"   💡 Suggestion: {error.suggestion}")
    
    if validation_result.warnings:
        print("\nWarnings:")
        for warning in validation_result.warnings:
            print(f"⚠️  {warning}")
    
    if validation_result.suggestions:
        print("\nHelpful suggestions:")
        for suggestion in validation_result.suggestions:
            print(f"💡 {suggestion}")
    
    print("\nPlease fix the configuration issues above and restart the application.")
    print("For more help, see the configuration documentation.")


def _handle_startup_health_failure(health_result: object) -> None:
    """Handle health check failures during application startup."""
    print(f"\n❌ LLM Service Health Check Failed: {health_result.service}")
    print("=" * 50)
    
    print(f"\nError: {health_result.error_message}")
    
    if health_result.details:
        if 'suggestion' in health_result.details:
            print(f"💡 Suggestion: {health_result.details['suggestion']}")
        
        if 'error_code' in health_result.details:
            print(f"Error Code: {health_result.details['error_code']}")
    
    print(f"\nPlease ensure {health_result.service} is properly configured and accessible.")
    print("For troubleshooting help, see the configuration documentation.") 