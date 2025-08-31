"""
Configuration normalization utilities for handling case-insensitive configuration
and environment variable overrides.
"""

import os
import logging
from typing import Dict, Any, Optional, Union
from configparser import ConfigParser

logger = logging.getLogger(__name__)


class ConfigNormalizer:
    """
    Normalizes configuration section names and handles case sensitivity issues.
    
    Provides case-insensitive configuration reading, section name normalization,
    duplicate section merging, and environment variable override functionality.
    """
    
    # Environment variable mapping: env_var -> (section, key)
    ENV_VAR_MAPPING = {
        'SYNC2NAS_LLM_SERVICE': ('llm', 'service'),
        'SYNC2NAS_OPENAI_API_KEY': ('openai', 'api_key'),
        'SYNC2NAS_OPENAI_MODEL': ('openai', 'model'),
        'SYNC2NAS_OPENAI_MAX_TOKENS': ('openai', 'max_tokens'),
        'SYNC2NAS_OPENAI_TEMPERATURE': ('openai', 'temperature'),
        'SYNC2NAS_ANTHROPIC_API_KEY': ('anthropic', 'api_key'),
        'SYNC2NAS_ANTHROPIC_MODEL': ('anthropic', 'model'),
        'SYNC2NAS_ANTHROPIC_MAX_TOKENS': ('anthropic', 'max_tokens'),
        'SYNC2NAS_ANTHROPIC_TEMPERATURE': ('anthropic', 'temperature'),
        'SYNC2NAS_OLLAMA_HOST': ('ollama', 'host'),
        'SYNC2NAS_OLLAMA_MODEL': ('ollama', 'model'),
        'SYNC2NAS_OLLAMA_NUM_CTX': ('ollama', 'num_ctx'),
    }
    
    # Section name aliases for case-insensitive handling
    SECTION_ALIASES = {
        'llm': ['LLM', 'Llm'],
        'openai': ['OpenAI', 'OPENAI', 'OpenAi'],
        'anthropic': ['Anthropic', 'ANTHROPIC', 'Anthropic'],
        'ollama': ['Ollama', 'OLLAMA', 'Ollama'],
        'sftp': ['SFTP', 'Sftp'],
        'database': ['Database', 'DATABASE', 'DataBase'],
        'tmdb': ['TMDB', 'Tmdb'],
        'transfers': ['Transfers', 'TRANSFERS'],
        'routing': ['Routing', 'ROUTING'],
    }
    
    def __init__(self):
        """Initialize the ConfigNormalizer."""
        self._normalized_cache: Dict[str, Dict[str, Any]] = {}
    
    def normalize_config(self, config: Union[ConfigParser, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Normalize configuration section names and merge duplicate sections.
        
        Args:
            config: Raw configuration from ConfigParser or dict
            
        Returns:
            dict: Normalized configuration with lowercase section names
        """
        logger.debug("Starting configuration normalization")
        
        # Convert ConfigParser to dict if needed
        if isinstance(config, ConfigParser):
            raw_config = {section: dict(config[section]) for section in config.sections()}
        else:
            raw_config = config.copy()
        
        normalized = {}
        section_mapping = self._build_section_mapping()
        
        # Process each section in the raw config
        for section_name, section_data in raw_config.items():
            # Find the canonical (lowercase) section name
            canonical_name = section_mapping.get(section_name.lower(), section_name.lower())
            
            # Normalize keys to lowercase as well
            normalized_section_data = {}
            for key, value in section_data.items():
                normalized_key = key.lower()
                # Special handling for service values - normalize to lowercase
                if normalized_key == 'service' and canonical_name == 'llm':
                    normalized_value = value.lower()
                else:
                    normalized_value = value
                normalized_section_data[normalized_key] = normalized_value
            
            if canonical_name in normalized:
                # Merge with existing section (lowercase takes precedence)
                logger.debug(f"Merging duplicate section: {section_name} -> {canonical_name}")
                if section_name.islower():
                    # Lowercase section takes precedence
                    normalized[canonical_name].update(normalized_section_data)
                else:
                    # Only add keys that don't exist in lowercase section
                    for key, value in normalized_section_data.items():
                        if key not in normalized[canonical_name]:
                            normalized[canonical_name][key] = value
            else:
                # First occurrence of this section
                normalized[canonical_name] = normalized_section_data
                logger.debug(f"Normalized section: {section_name} -> {canonical_name}")
        
        logger.info(f"Configuration normalization complete. Sections: {list(normalized.keys())}")
        return normalized
    
    def apply_env_overrides(self, config: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Apply environment variable overrides to configuration.
        
        Args:
            config: Normalized configuration dict
            
        Returns:
            dict: Configuration with environment variable overrides applied
        """
        logger.debug("Applying environment variable overrides")
        
        config_with_overrides = {}
        for section, section_data in config.items():
            config_with_overrides[section] = section_data.copy()
        
        overrides_applied = 0
        
        # Apply environment variable overrides
        for env_var, (section, key) in self.ENV_VAR_MAPPING.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Ensure section exists
                if section not in config_with_overrides:
                    config_with_overrides[section] = {}
                
                # Apply override
                old_value = config_with_overrides[section].get(key, '<not set>')
                config_with_overrides[section][key] = env_value
                overrides_applied += 1
                
                logger.info(f"Environment override applied: {env_var} -> [{section}] {key}")
                logger.debug(f"Value changed: {old_value} -> {env_value}")
        
        if overrides_applied > 0:
            logger.info(f"Applied {overrides_applied} environment variable overrides")
        else:
            logger.debug("No environment variable overrides found")
        
        return config_with_overrides
    
    def get_normalized_value(
        self, 
        config: Dict[str, Dict[str, Any]], 
        section: str, 
        key: str, 
        fallback: Any = None
    ) -> Any:
        """
        Get configuration value with case-insensitive lookup.
        
        Args:
            config: Normalized configuration dict
            section: Section name (will be normalized)
            key: Configuration key
            fallback: Default value if not found
            
        Returns:
            Configuration value or fallback
        """
        # Normalize section name
        section_mapping = self._build_section_mapping()
        canonical_section = section_mapping.get(section.lower(), section.lower())
        
        # Get value from normalized config
        section_data = config.get(canonical_section, {})
        return section_data.get(key, fallback)
    
    def normalize_and_override(self, config: Union[ConfigParser, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Complete normalization pipeline: normalize sections and apply environment overrides.
        
        Args:
            config: Raw configuration from ConfigParser or dict
            
        Returns:
            dict: Fully normalized and overridden configuration
        """
        logger.debug("Starting complete configuration normalization pipeline")
        
        # Step 1: Normalize section names and merge duplicates
        normalized = self.normalize_config(config)
        
        # Step 2: Apply environment variable overrides
        final_config = self.apply_env_overrides(normalized)
        
        logger.info("Configuration normalization pipeline complete")
        return final_config
    
    def _build_section_mapping(self) -> Dict[str, str]:
        """
        Build a mapping from all possible section names to their canonical lowercase form.
        
        Returns:
            dict: Mapping of section_name.lower() -> canonical_name
        """
        mapping = {}
        
        for canonical, aliases in self.SECTION_ALIASES.items():
            # Map canonical name to itself
            mapping[canonical.lower()] = canonical
            
            # Map all aliases to canonical name
            for alias in aliases:
                mapping[alias.lower()] = canonical
        
        return mapping
    
    def get_supported_env_vars(self) -> Dict[str, tuple]:
        """
        Get all supported environment variables and their mappings.
        
        Returns:
            dict: Environment variable mapping
        """
        return self.ENV_VAR_MAPPING.copy()
    
    def clear_cache(self) -> None:
        """Clear the normalization cache."""
        self._normalized_cache.clear()
        logger.debug("Configuration normalization cache cleared")