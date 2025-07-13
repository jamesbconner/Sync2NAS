"""
Configuration utilities for loading, parsing, and writing Sync2NAS config files.
"""
import configparser
from pathlib import Path

def load_configuration(path: str) -> configparser.ConfigParser:
    """
    Load the configuration file.

    Args:
        path (str): Path to the configuration file.

    Returns:
        configparser.ConfigParser: Loaded configuration parser.
    """
    parser = configparser.ConfigParser()
    parser.read(path)
    return parser

def parse_sftp_paths(config: configparser.ConfigParser) -> list:
    """
    Parse the SFTP paths from the config file.

    Args:
        config (configparser.ConfigParser): Loaded configuration parser.

    Returns:
        list: List of SFTP paths as strings.
    """
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