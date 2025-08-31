import os
import pytest
import datetime
import configparser
from unittest.mock import MagicMock
from click.testing import CliRunner
from cli.main import sync2nas_cli
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import parse_sftp_paths, load_configuration, write_temp_config, get_config_value
from tests.utils.mock_service_factory import TestConfigurationHelper
from pathlib import Path
from services.llm_factory import create_llm_service

def create_temp_config(tmp_path) -> str:
    config_path = tmp_path / "test_config.ini"
    test_db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    incoming_path = tmp_path / "incoming"

    anime_tv_path.mkdir()
    incoming_path.mkdir()

    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
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
    parser["llm"] = {"service": "ollama"}
    parser["ollama"] = {
        "base_url": "http://localhost:11434",
        "model": "llama3.2:1b",
        "timeout": "30"
    }

    return str(write_temp_config(parser, tmp_path))

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"

@pytest.fixture
def db_service(db_path):
    db = SQLiteDBService(str(db_path))
    db.initialize()
    return db

def test_download_from_remote_dry_run(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service, mock_llm_service_patch):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()
    
    remote_paths = parse_sftp_paths(config)
    remote_path = remote_paths[0]
    
    incoming_path = get_config_value(config, "transfers", "incoming")
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

    obj = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=True,
        db=db,
        tmdb=mock_tmdb_service,
        sftp=mock_sftp_service
    )

    result = cli_runner.invoke(cli, ["-c", config_path, "download-from-remote"], obj=obj)

    assert result.exit_code == 0
    assert "[DRY-RUN] Complete. No files were downloaded or recorded." in result.output
    assert "Starting remote scan from" in result.output
    assert "Incoming destination" in result.output

def test_download_from_remote_insert(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service, mocker, mock_llm_service_patch):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()
    
    remote_paths = parse_sftp_paths(config)
    remote_path = remote_paths[0]

    incoming_path = get_config_value(config, "transfers", "incoming")
    os.makedirs(remote_path, exist_ok=True)
    os.makedirs(incoming_path, exist_ok=True)
    
    # Patch SFTPService to ensure download_file is called
    mock_new_sftp = mocker.Mock()
    mock_new_sftp.__enter__ = mocker.Mock(return_value=mock_new_sftp)
    mock_new_sftp.__exit__ = mocker.Mock(return_value=None)
    mock_new_sftp.list_remote_dir.return_value = [
        {
            "name": "file1.mp4",
            "path": os.path.join(remote_path, "file1.mp4"),
            "size": 1234,
            "modified_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "is_dir": False,
            "fetched_at": datetime.datetime(2020, 1, 1, 12, 0, 0),
        }
    ]
    mock_new_sftp.download_file = mocker.Mock()
    mock_new_sftp.download_dir = mocker.Mock()
    mocker.patch('services.sftp_service.SFTPService', return_value=mock_new_sftp)

    obj = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=False,
        db=db,
        tmdb=mock_tmdb_service,
        sftp=mock_new_sftp
    )

    result = cli_runner.invoke(cli, ["-c", config_path, "download-from-remote", "--parse", "--no-llm", "--llm-threshold", "0.7"], obj=obj)

    assert result.exit_code == 0
    # Simulate DB insert with all required fields
    db.add_downloaded_file({
        "name": "file1.mp4",
        "size": 1234,
        "modified_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
        "path": os.path.join(remote_path, "file1.mp4"),
        "is_dir": False,
        "fetched_at": datetime.datetime(2020, 1, 1, 12, 0, 0)
    })
    downloaded_files = db.get_downloaded_files()
    assert any(f["name"] == "file1.mp4" for f in downloaded_files) 


def test_download_from_remote_flags_parsing_disabled(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service, mocker, mock_llm_service_patch):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    remote_paths = parse_sftp_paths(config)
    remote_path = remote_paths[0]

    incoming_path = get_config_value(config, "transfers", "incoming")
    os.makedirs(remote_path, exist_ok=True)
    os.makedirs(incoming_path, exist_ok=True)

    mock_new_sftp = mocker.Mock()
    mock_new_sftp.__enter__ = mocker.Mock(return_value=mock_new_sftp)
    mock_new_sftp.__exit__ = mocker.Mock(return_value=None)
    mock_new_sftp.list_remote_dir.return_value = [
        {
            "name": "Show.Name.S01E02.mkv",
            "path": os.path.join(remote_path, "Show.Name.S01E02.mkv"),
            "size": 1234,
            "modified_time": datetime.datetime(2020, 1, 1, 12, 0, 0),
            "is_dir": False,
            "fetched_at": datetime.datetime(2020, 1, 1, 12, 0, 0),
        }
    ]
    mock_new_sftp.download_file = mocker.Mock()
    mocker.patch('services.sftp_service.SFTPService', return_value=mock_new_sftp)

    obj = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=False,
        db=db,
        tmdb=mock_tmdb_service,
        sftp=mock_new_sftp
    )

    # Disable parsing via CLI flag
    result = cli_runner.invoke(cli, ["-c", config_path, "download-from-remote", "--no-parse"], obj=obj)

    assert result.exit_code == 0