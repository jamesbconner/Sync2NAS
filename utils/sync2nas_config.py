import configparser
from pathlib import Path

def load_configuration(path: str) -> configparser.ConfigParser:
    """Load the configuration file."""
    parser = configparser.ConfigParser()
    parser.read(path)
    return parser

def parse_sftp_paths(config):
    """Parse the SFTP paths from the config file. Returns a list of paths."""
    raw_paths = config.get("SFTP", "paths", fallback="")
    return [p.strip() for p in raw_paths.split(",") if p.strip()]

def write_temp_config(config_dict, tmp_path):
    """
    Write a temporary config.ini file from a dictionary of config sections.
    Returns the path to the config file.
    """
    config = configparser.ConfigParser()
    for section, values in config_dict.items():
        config[section] = values

    config_path = Path(tmp_path) / "test_sync2nas_config.ini"
    with open(config_path, "w") as f:
        config.write(f)

    return config_path