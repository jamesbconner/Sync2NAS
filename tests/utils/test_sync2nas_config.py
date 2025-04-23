import pytest
import configparser
from utils.sync2nas_config import parse_sftp_paths

def test_parse_multiple_paths_from_config():
    config = configparser.ConfigParser()
    config["SFTP"] = {"paths": "/a,/b , /c/"}
    assert parse_sftp_paths(config) == ["/a", "/b", "/c/"]

def test_parse_single_path_from_config():
    config = configparser.ConfigParser()
    config["SFTP"] = {"paths": "/a"}
    assert parse_sftp_paths(config) == ["/a"]
    