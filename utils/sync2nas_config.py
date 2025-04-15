import configparser
from pathlib import Path

def load_configuration(path: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(path)
    return parser

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