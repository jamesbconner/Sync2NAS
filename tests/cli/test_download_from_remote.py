import os
import pytest
import datetime
import configparser
from unittest.mock import MagicMock
from click.testing import CliRunner
from cli.main import sync2nas_cli
from services.db_service import DBService
from utils.sync2nas_config import parse_sftp_paths, load_configuration, write_temp_config
from pathlib import Path

def create_temp_config(tmp_path) -> str:
    config_path = tmp_path / "test_config.ini"
    test_db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    incoming_path = tmp_path / "incoming"

    anime_tv_path.mkdir()
    incoming_path.mkdir()

    parser = configparser.ConfigParser()
    parser["SQLite"] = {"db_file": str(test_db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(incoming_path)}
    parser["SFTP"] = {
        "host": "localhost",
        "port": "22",
        "username": "testuser",
        "ssh_key_path": str(tmp_path / "dummy_key"),
        "paths": str(tmp_path / "remote")
    }
    parser["TMDB"] = {"api_key": "dummy"}

    return str(write_temp_config(parser, tmp_path))

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"

@pytest.fixture
def db_service(db_path):
    db = DBService(str(db_path))
    db.initialize()
    return db

def test_download_from_remote_dry_run(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()
    
    remote_paths = parse_sftp_paths(config)
    remote_path = remote_paths[0]
    
    incoming_path = config["Transfers"]["incoming"]
    os.makedirs(remote_path, exist_ok=True)
    os.makedirs(incoming_path, exist_ok=True)

    # Mock the SFTP service to return a list of files
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": os.path.join(remote_path, "file1.mkv"),
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        }
    ]

    # Ensure the mock supports the context manager protocol
    mock_sftp_service = MagicMock()
    mock_sftp_service.__enter__.return_value = mock_sftp_service

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": incoming_path
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "download-from-remote", "--dry-run"], obj=obj)

    assert result.exit_code == 0
    assert "Dry run complete. No files were downloaded or recorded." in result.output
    assert "Starting remote scan from" in result.output
    assert "Incoming destination" in result.output

def test_download_from_remote_insert(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()
    
    remote_paths = parse_sftp_paths(config)
    remote_path = remote_paths[0]

    incoming_path = config["Transfers"]["incoming"]
    os.makedirs(remote_path, exist_ok=True)
    os.makedirs(incoming_path, exist_ok=True)
    
    # Ensure the mock supports the context manager protocol
    mock_sftp_service = MagicMock()
    mock_sftp_service.__enter__.return_value = mock_sftp_service
    
    # Mock the SFTP service to return a list of files
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mp4",
            "path": os.path.join(remote_path, "file1.mp4"),
            "size": 1234,
            "modified_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "is_dir": False,
            "fetched_at": datetime.datetime(2020, 1, 1, 12, 0, 0),
        }
    ]

    mock_sftp_service.download_file = MagicMock()
    mock_sftp_service.download_dir = MagicMock()

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": incoming_path
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "download-from-remote"], obj=obj)

    assert result.exit_code == 0

    # Verify that the file was actually downloaded and recorded
    downloaded_files = db.get_downloaded_files()
    assert len(downloaded_files) == 1
    assert downloaded_files[0]["name"] == "file1.mp4" 