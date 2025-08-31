"""
Configuration utilities for loading, parsing, and writing Sync2NAS config files.
"""
import configparser
import logging
from pathlib import Path
from typing import Dict, Any, Union, List
from utils.config.config_normalizer import ConfigNormalizer

logger = logging.getLogger(__name__)

def load_configuration(path: str, normalize: bool = True) -> Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]]:
    """
    Load the configuration file with optional normalization.

    Args:
        path (str): Path to the configuration file.
        normalize (bool): Whether to apply configuration normalization and environment overrides.

    Returns:
        Union[configparser.ConfigParser, Dict]: Loaded configuration parser or normalized dict.
    """
    parser = configparser.ConfigParser()
    parser.read(path)
    
    if normalize:
        logger.debug(f"Loading and normalizing configuration from: {path}")
        normalizer = ConfigNormalizer()
        normalized_config = normalizer.normalize_and_override(parser)
        logger.info(f"Configuration loaded and normalized successfully from: {path}")
        return normalized_config
    else:
        logger.debug(f"Loading raw configuration from: {path}")
        return parser


def load_configuration_raw(path: str) -> configparser.ConfigParser:
    """
    Load the raw configuration file without normalization (for backward compatibility).

    Args:
        path (str): Path to the configuration file.

    Returns:
        configparser.ConfigParser: Loaded configuration parser.
    """
    return load_configuration(path, normalize=False)

def parse_sftp_paths(config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]]) -> list:
    """
    Parse the SFTP paths from the config file.

    Args:
        config: Loaded configuration parser or normalized dict.

    Returns:
        list: List of SFTP paths as strings.
    """
    if isinstance(config, dict):
        # Handle normalized configuration dict
        sftp_section = config.get("sftp", {})
        raw_paths = sftp_section.get("paths", "")
    else:
        # Handle ConfigParser
        raw_paths = config.get("SFTP", "paths", fallback="")
    
    return [p.strip() for p in raw_paths.split(",") if p.strip()]

def write_temp_config(config_dict: dict, tmp_path: str) -> Path:
    """
    Write a temporary config.ini file from a dictionary of config sections.

    Args:
        config_dict (dict): Dictionary of config sections and values.
        tmp_path (str): Path to temporary directory.

    Returns:
        Path: Path to the written config file.
    """
    config = configparser.ConfigParser()
    for section, values in config_dict.items():
        config[section] = values

    config_path = Path(tmp_path) / "test_sync2nas_config.ini"
    with open(config_path, "w") as f:
        config.write(f)

    return config_path


def _get_key_variations(key: str) -> List[str]:
    """
    Generate case variations for a configuration key.
    
    Args:
        key: Original key name
        
    Returns:
        List[str]: List of key variations to try
    """
    variations = [
        key,  # Original key
        key.lower(),  # lowercase
        key.upper(),  # UPPERCASE
        key.title(),  # Title Case
        key.capitalize(),  # Capitalize first letter
    ]
    
    # Handle common patterns like timeout -> TimeOut
    if '_' in key:
        # snake_case to PascalCase
        variations.append(''.join(word.capitalize() for word in key.split('_')))
        # Remove underscores with different cases
        no_underscore = key.replace('_', '')
        variations.extend([
            no_underscore.lower(),
            no_underscore.upper(), 
            no_underscore.title(),
            no_underscore.capitalize()
        ])
    else:
        # Handle camelCase variations and common compound word patterns
        if len(key) > 1:
            # Try first letter upper, rest lower
            variations.append(key[0].upper() + key[1:].lower())
            
            # Special handling for common compound words
            # Look for common word boundaries and capitalize appropriately
            common_patterns = {
                'timeout': ['TimeOut', 'Timeout'],
                'maxsize': ['MaxSize', 'Maxsize'],
                'minsize': ['MinSize', 'Minsize'],
                'apikey': ['ApiKey', 'APIKey', 'Apikey'],
                'username': ['UserName', 'Username'],
                'hostname': ['HostName', 'Hostname'],
                'filename': ['FileName', 'Filename'],
                'filepath': ['FilePath', 'Filepath'],
                'database': ['DataBase', 'Database'],
                'baseurl': ['BaseUrl', 'BaseURL', 'Baseurl'],
            }
            
            key_lower = key.lower()
            if key_lower in common_patterns:
                variations.extend(common_patterns[key_lower])
            
            # Try splitting at common word boundaries and capitalizing
            for i in range(2, len(key)):
                # Try splitting at position i
                part1 = key[:i]
                part2 = key[i:]
                variations.append(part1.capitalize() + part2.capitalize())
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        if var not in seen:
            seen.add(var)
            unique_variations.append(var)
    
    return unique_variations


def get_config_value(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]], 
    section: str, 
    key: str, 
    fallback: Any = None,
    value_type: type = str
) -> Any:
    """
    Get a configuration value with case-insensitive lookup and type conversion.
    
    Args:
        config: Configuration object (ConfigParser or normalized dict)
        section: Configuration section name
        key: Configuration key name
        fallback: Default value if not found
        value_type: Type to convert the value to (str, int, float, bool)
        
    Returns:
        Configuration value converted to specified type or fallback
        
    Raises:
        ValueError: If value cannot be converted to specified type
        TypeError: If config is not a supported type
    """
    if config is None:
        return fallback
    
    if not isinstance(section, str) or not section.strip():
        raise ValueError("Section name must be a non-empty string")
    
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Key name must be a non-empty string")
    
    section = section.strip()
    key = key.strip()
    
    # Initialize value to fallback to ensure it's always defined
    value = fallback
    
    try:
        if isinstance(config, dict):
            # Handle normalized configuration dict with case-insensitive key lookup
            try:
                section_data = get_config_section(config, section)
                # Try case variations for the key
                key_variations = _get_key_variations(key)
                for key_var in key_variations:
                    if key_var in section_data:
                        value = section_data[key_var]
                        break
            except ValueError:
                # Section not found, keep fallback value
                pass
        elif isinstance(config, configparser.ConfigParser):
            # Handle ConfigParser with case-insensitive section lookup
            try:
                section_data = get_config_section(config, section)
                # Try case variations for the key
                key_variations = _get_key_variations(key)
                for key_var in key_variations:
                    if key_var in section_data:
                        value = section_data[key_var]
                        break
            except ValueError:
                # Section not found, keep fallback value
                pass
        else:
            # For unsupported config types, try to use duck typing
            # This allows test DummyConfig classes to work
            try:
                # Try to get the value using the get method
                if hasattr(config, 'get'):
                    value = config.get(section, key, fallback)
                else:
                    raise TypeError(
                        f"Unsupported configuration type: {type(config)}. "
                        f"Expected ConfigParser, Dict[str, Dict[str, Any]], or object with get() method"
                    )
            except Exception:
                # If duck typing fails, use fallback
                value = fallback
        
        # Return fallback if value is None or empty string
        if value is None or (isinstance(value, str) and not value.strip()):
            return fallback
        
        # Convert to specified type
        if value_type == bool and isinstance(value, str):
            # Handle boolean conversion from string
            return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        elif value_type == int:
            return int(value)
        elif value_type == float:
            return float(value)
        elif value_type == str:
            return str(value)
        else:
            return value_type(value)
            
    except (ValueError, TypeError) as e:
        if fallback is not None:
            logger.warning(
                f"Failed to convert config value [{section}].{key}='{value}' to {value_type.__name__}: {e}. "
                f"Using fallback: {fallback}"
            )
            return fallback
        else:
            raise ValueError(
                f"Failed to convert config value [{section}].{key}='{value}' to {value_type.__name__}: {e}"
            )


def get_config_section(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]], 
    section_name: str
) -> Dict[str, Any]:
    """
    Get configuration section with case-insensitive lookup and comprehensive error handling.
    
    Args:
        config: Configuration object (ConfigParser or normalized dict)
        section_name: Configuration section name
        
    Returns:
        Dict[str, Any]: Configuration section data
        
    Raises:
        ValueError: If section is not found
        TypeError: If config is not a supported type
    """
    if config is None:
        raise ValueError("Configuration object cannot be None")
    
    if not isinstance(section_name, str) or not section_name.strip():
        raise ValueError("Section name must be a non-empty string")
    
    section_name = section_name.strip()
    
    if isinstance(config, dict):
        # Handle normalized configuration dict
        normalizer = ConfigNormalizer()
        section_mapping = normalizer._build_section_mapping()
        canonical_name = section_mapping.get(section_name.lower(), section_name.lower())
        
        if canonical_name in config:
            return config[canonical_name].copy()  # Return copy to prevent modification
        else:
            available_sections = sorted(config.keys())
            raise ValueError(
                f"Configuration section '{section_name}' not found. "
                f"Available sections: {available_sections}"
            )
    elif isinstance(config, configparser.ConfigParser):
        # Handle ConfigParser - try case variations
        section_variations = [
            section_name, 
            section_name.upper(), 
            section_name.lower(), 
            section_name.title(),
            section_name.capitalize()
        ]
        
        # Add common variations for specific sections
        if section_name.lower() == 'sqlite':
            section_variations.append('SQLite')
        elif section_name.lower() == 'sftp':
            section_variations.append('SFTP')
        elif section_name.lower() == 'tmdb':
            section_variations.append('TMDB')
        elif section_name.lower() == 'llm':
            section_variations.append('LLM')
        
        for variation in section_variations:
            if config.has_section(variation):
                return dict(config[variation])
        
        available_sections = sorted(config.sections())
        raise ValueError(
            f"Configuration section '{section_name}' not found. "
            f"Available sections: {available_sections}"
        )
    else:
        raise TypeError(
            f"Unsupported configuration type: {type(config)}. "
            f"Expected ConfigParser or Dict[str, Dict[str, Any]]"
        )


def validate_test_config(config: Dict[str, Dict[str, Any]]) -> bool:
    """
    Validate that configuration is suitable for testing with comprehensive checks.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        bool: True if configuration is valid for testing
        
    Raises:
        ValueError: If configuration is invalid with detailed error message
        TypeError: If config is not a dictionary
    """
    if not isinstance(config, dict):
        raise TypeError(f"Configuration must be a dictionary, got {type(config)}")
    
    if not config:
        raise ValueError("Configuration cannot be empty")
    
    validation_errors = []
    
    # Check required sections
    required_sections = ["database", "llm"]
    missing_sections = []
    
    for section in required_sections:
        if not has_config_section(config, section):
            missing_sections.append(section)
    
    if missing_sections:
        validation_errors.append(f"Missing required sections: {missing_sections}")
    
    # Validate database configuration
    if has_config_section(config, "database"):
        database_config = get_config_section(config, "database")
        db_type = database_config.get("type", "").strip().lower()
        
        if not db_type:
            validation_errors.append("Database type is required for testing")
        elif db_type == "sqlite":
            if not has_config_section(config, "sqlite"):
                validation_errors.append("SQLite configuration section is required when using SQLite database")
            else:
                sqlite_config = get_config_section(config, "sqlite")
                db_file = sqlite_config.get("db_file", "").strip()
                if not db_file:
                    validation_errors.append("SQLite db_file is required when using SQLite database")
        elif db_type == "postgresql":
            if not has_config_section(config, "postgresql"):
                validation_errors.append("PostgreSQL configuration section is required when using PostgreSQL database")
            else:
                pg_config = get_config_section(config, "postgresql")
                required_pg_keys = ["host", "port", "database", "username"]
                for key in required_pg_keys:
                    if not pg_config.get(key, "").strip():
                        validation_errors.append(f"PostgreSQL {key} is required when using PostgreSQL database")
        elif db_type not in ["sqlite", "postgresql", "milvus"]:
            validation_errors.append(f"Unsupported database type: {db_type}. Supported types: sqlite, postgresql, milvus")
    
    # Validate LLM configuration
    if has_config_section(config, "llm"):
        llm_config = get_config_section(config, "llm")
        llm_service = llm_config.get("service", "").strip().lower()
        
        if not llm_service:
            validation_errors.append("LLM service is required for testing")
        elif llm_service == "ollama":
            if not has_config_section(config, "ollama"):
                validation_errors.append("Ollama configuration section is required when using Ollama LLM service")
            else:
                ollama_config = get_config_section(config, "ollama")
                if not ollama_config.get("model", "").strip():
                    validation_errors.append("Ollama model is required when using Ollama LLM service")
        elif llm_service == "openai":
            if not has_config_section(config, "openai"):
                validation_errors.append("OpenAI configuration section is required when using OpenAI LLM service")
            else:
                openai_config = get_config_section(config, "openai")
                if not openai_config.get("api_key", "").strip():
                    validation_errors.append("OpenAI API key is required when using OpenAI LLM service")
                if not openai_config.get("model", "").strip():
                    validation_errors.append("OpenAI model is required when using OpenAI LLM service")
        elif llm_service == "anthropic":
            if not has_config_section(config, "anthropic"):
                validation_errors.append("Anthropic configuration section is required when using Anthropic LLM service")
            else:
                anthropic_config = get_config_section(config, "anthropic")
                if not anthropic_config.get("api_key", "").strip():
                    validation_errors.append("Anthropic API key is required when using Anthropic LLM service")
                if not anthropic_config.get("model", "").strip():
                    validation_errors.append("Anthropic model is required when using Anthropic LLM service")
        elif llm_service not in ["ollama", "openai", "anthropic"]:
            validation_errors.append(f"Unsupported LLM service: {llm_service}. Supported services: ollama, openai, anthropic")
    
    # Optional validation for commonly used sections in tests
    optional_validations = []
    
    # Validate SFTP configuration if present
    if has_config_section(config, "sftp"):
        sftp_config = get_config_section(config, "sftp")
        if not sftp_config.get("host", "").strip():
            optional_validations.append("SFTP host is recommended for complete testing")
    
    # Validate TMDB configuration if present
    if has_config_section(config, "tmdb"):
        tmdb_config = get_config_section(config, "tmdb")
        if not tmdb_config.get("api_key", "").strip():
            optional_validations.append("TMDB API key is recommended for complete testing")
    
    # Log optional validation warnings
    if optional_validations:
        logger.warning(f"Optional validation warnings: {optional_validations}")
    
    # Raise error if there are validation errors
    if validation_errors:
        error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
        raise ValueError(error_message)
    
    logger.debug("Configuration validation passed successfully")
    return True


def get_config_int(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]], 
    section: str, 
    key: str, 
    fallback: int = 0
) -> int:
    """
    Get configuration value as integer with fallback.
    
    Args:
        config: Configuration object
        section: Configuration section name
        key: Configuration key name
        fallback: Default integer value if not found or invalid
        
    Returns:
        int: Configuration value as integer or fallback
    """
    return get_config_value(config, section, key, fallback, int)


def get_config_float(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]], 
    section: str, 
    key: str, 
    fallback: float = 0.0
) -> float:
    """
    Get configuration value as float with fallback.
    
    Args:
        config: Configuration object
        section: Configuration section name
        key: Configuration key name
        fallback: Default float value if not found or invalid
        
    Returns:
        float: Configuration value as float or fallback
    """
    return get_config_value(config, section, key, fallback, float)


def get_config_bool(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]], 
    section: str, 
    key: str, 
    fallback: bool = False
) -> bool:
    """
    Get configuration value as boolean with fallback.
    
    Args:
        config: Configuration object
        section: Configuration section name
        key: Configuration key name
        fallback: Default boolean value if not found or invalid
        
    Returns:
        bool: Configuration value as boolean or fallback
    """
    return get_config_value(config, section, key, fallback, bool)


def get_config_string(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]], 
    section: str, 
    key: str, 
    fallback: str = ""
) -> str:
    """
    Get configuration value as string with fallback.
    
    Args:
        config: Configuration object
        section: Configuration section name
        key: Configuration key name
        fallback: Default string value if not found
        
    Returns:
        str: Configuration value as string or fallback
    """
    return get_config_value(config, section, key, fallback, str)


def has_config_section(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]], 
    section_name: str
) -> bool:
    """
    Check if configuration section exists (case-insensitive).
    
    Args:
        config: Configuration object
        section_name: Configuration section name
        
    Returns:
        bool: True if section exists, False otherwise
    """
    try:
        get_config_section(config, section_name)
        return True
    except (ValueError, TypeError):
        return False


def has_config_key(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]], 
    section: str, 
    key: str
) -> bool:
    """
    Check if configuration key exists in section (case-insensitive).
    
    Args:
        config: Configuration object
        section: Configuration section name
        key: Configuration key name
        
    Returns:
        bool: True if key exists in section, False otherwise
    """
    try:
        section_data = get_config_section(config, section)
        key_variations = _get_key_variations(key)
        return any(key_var in section_data for key_var in key_variations)
    except (ValueError, TypeError):
        return False


def get_config_sections(
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]]
) -> List[str]:
    """
    Get list of all configuration sections.
    
    Args:
        config: Configuration object
        
    Returns:
        List[str]: List of section names
    """
    if isinstance(config, dict):
        return list(config.keys())
    elif isinstance(config, configparser.ConfigParser):
        return config.sections()
    else:
        raise TypeError(
            f"Unsupported configuration type: {type(config)}. "
            f"Expected ConfigParser or Dict[str, Dict[str, Any]]"
        )


def create_config_normalizer() -> ConfigNormalizer:
    """
    Create a new ConfigNormalizer instance.
    
    Returns:
        ConfigNormalizer: New normalizer instance
    """
    return ConfigNormalizer()