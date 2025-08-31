import os
import pytest
import configparser
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from cli.main import sync2nas_cli
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import load_configuration, write_temp_config, get_config_value
from tests.utils.mock_service_factory import TestConfigurationHelper
from pathlib import Path
from cli.list_remote import list_remote
from datetime import datetime
from services.llm_factory import create_llm_service

def create_temp_config(tmp_path: Path) -> str:
    config_path = tmp_path / "test_config.ini"
    test_db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    incoming_path = tmp_path / "incoming"
    remote_path = tmp_path / "remote"

    anime_tv_path.mkdir()
    incoming_path.mkdir()
    remote_path.mkdir()

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
        "paths": str(remote_path)
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
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"

@pytest.fixture
def db_service(db_path: Path):
    db = SQLiteDBService(str(db_path))
    db.initialize()
    return db

@pytest.fixture
def mock_sftp_service():
    mock = MagicMock()
    mock.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": "/path/to/file1.mkv",
            "size": 100,
            "modified_time": datetime.now(),
            "is_dir": False,
            "fetched_at": datetime.now()
        },
        {
            "name": "dir1",
            "path": "/path/to/dir1",
            "size": 0,
            "modified_time": datetime.now(),
            "is_dir": True,
            "fetched_at": datetime.now()
        }
    ]
    mock.list_remote_files_recursive.return_value = [
        {
            "name": "file1.mkv",
            "path": "/path/to/file1.mkv",
            "size": 100,
            "modified_time": datetime.now(),
            "is_dir": False,
            "fetched_at": datetime.now()
        },
        {
            "name": "dir1",
            "path": "/path/to/dir1",
            "size": 0,
            "modified_time": datetime.now(),
            "is_dir": True,
            "fetched_at": datetime.now()
        }
    ]
    return mock

@pytest.fixture
def mock_db():
    mock = MagicMock()
    mock.insert_sftp_temp_files.return_value = None
    return mock

@pytest.fixture
def mock_config():
    return {"sftp": {"paths": "/remote/path"}}

def test_list_remote_basic(tmp_path: Path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service, mock_llm_service_patch):
    """Test basic remote listing without options"""
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    remote_path = Path(get_config_value(config, "sftp", "paths"))
    incoming_path = Path(get_config_value(config, "transfers", "incoming"))
    remote_path.mkdir(exist_ok=True)
    incoming_path.mkdir(exist_ok=True)

    # Mock the SFTP service to return a list of files
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": str(remote_path / "file1.mkv"),
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        }
    ]

    # Ensure the mock supports the context manager protocol
    mock_sftp_service.__enter__ = lambda self: self
    mock_sftp_service.__exit__ = lambda self, *args: None

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": str(incoming_path),
        "dry_run": False
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "--skip-validation", "list-remote"], obj=obj)
    assert result.exit_code == 0
    assert "file1.mkv" in result.output

def test_list_remote_with_path(tmp_path: Path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service, mock_llm_service_patch):
    """Test remote listing with custom path"""
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    remote_path = Path(get_config_value(config, "sftp", "paths"))
    incoming_path = Path(get_config_value(config, "transfers", "incoming"))
    remote_path.mkdir(exist_ok=True)
    incoming_path.mkdir(exist_ok=True)

    # Mock the SFTP service to return a list of files
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": str(remote_path / "file1.mkv"),
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        }
    ]

    # Ensure the mock supports the context manager protocol
    mock_sftp_service.__enter__ = lambda self: self
    mock_sftp_service.__exit__ = lambda self, *args: None

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": str(incoming_path),
        "dry_run": False
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "--skip-validation", "list-remote", "--path", "/custom/path"], obj=obj)
    assert result.exit_code == 0
    assert "file1.mkv" in result.output

def test_list_remote_dry_run(tmp_path: Path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service, mock_llm_service_patch):
    """Test remote listing in dry run mode"""
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    remote_path = Path(get_config_value(config, "sftp", "paths"))
    incoming_path = Path(get_config_value(config, "transfers", "incoming"))
    remote_path.mkdir(exist_ok=True)
    incoming_path.mkdir(exist_ok=True)

    # Mock the SFTP service to return a list of files
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": str(remote_path / "file1.mkv"),
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        }
    ]

    # Ensure the mock supports the context manager protocol
    mock_sftp_service.__enter__ = lambda self: self
    mock_sftp_service.__exit__ = lambda self, *args: None

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": MagicMock(),  # Provide a mock LLM service
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": str(incoming_path),
        "dry_run": True  # Set dry_run to True
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "--skip-validation", "list-remote"], obj=obj)
    assert result.exit_code == 0
    assert "Dry run: Would list" in result.output

def test_list_remote_with_recursive(tmp_path: Path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service, mock_llm_service_patch):
    """Test remote listing with recursive option"""
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    remote_path = Path(get_config_value(config, "sftp", "paths"))
    incoming_path = Path(get_config_value(config, "transfers", "incoming"))
    remote_path.mkdir(exist_ok=True)
    incoming_path.mkdir(exist_ok=True)

    # Mock the SFTP service to return a list of files including a directory
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": str(remote_path / "file1.mkv"),
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        },
        {
            "name": "dir1",
            "path": str(remote_path / "dir1"),
            "size": 0,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": True,
            "fetched_at": "2020-01-01 12:00:00"
        }
    ]

    # Ensure the mock supports the context manager protocol
    mock_sftp_service.__enter__ = lambda self: self
    mock_sftp_service.__exit__ = lambda self, *args: None

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": MagicMock(),  # Provide a mock LLM service
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": str(incoming_path),
        "dry_run": False
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "--skip-validation", "list-remote", "--recursive"], obj=obj)
    assert result.exit_code == 0
    assert "file1.mkv" in result.output
    assert "dir1" in result.output

def test_list_remote_with_populate_sftp_temp(tmp_path: Path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service, mock_llm_service_patch):
    """Test remote listing with populate_sftp_temp option"""
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    remote_path = Path(get_config_value(config, "sftp", "paths"))
    incoming_path = Path(get_config_value(config, "transfers", "incoming"))
    remote_path.mkdir(exist_ok=True)
    incoming_path.mkdir(exist_ok=True)

    # Create a consistent datetime object for both timestamps
    now = datetime.now()
    
    # Mock the SFTP service to return a list of files with datetime objects
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": str(remote_path / "file1.mkv"),
            "size": 100,
            "modified_time": now,
            "is_dir": False,
            "fetched_at": now
        }
    ]

    # Ensure the mock supports the context manager protocol
    mock_sftp_service.__enter__ = lambda self: self
    mock_sftp_service.__exit__ = lambda self, *args: None

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": MagicMock(),  # Provide a mock LLM service
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": str(incoming_path),
        "dry_run": False
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "--skip-validation", "list-remote", "--populate-sftp-temp"], obj=obj)
    assert result.exit_code == 0
    assert "file1.mkv" in result.output
    assert "Populated sftp_temp table" in result.output

def test_list_remote_default(mock_sftp_service, mock_db, mock_config, mock_llm_service_patch):
    runner = CliRunner()
    
    # Ensure the mock supports the context manager protocol
    mock_sftp_service.__enter__ = lambda self: self
    mock_sftp_service.__exit__ = lambda self, *args: None
    
    # Set up mock data with string timestamps to match other tests
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": "/path/to/file1.mkv",
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        }
    ]
    
    result = runner.invoke(list_remote, obj={
        "sftp": mock_sftp_service,
        "db": mock_db,
        "config": mock_config,
        "dry_run": False
    })
    assert result.exit_code == 0
    assert "file1.mkv" in result.output

def test_list_remote_recursive(mock_sftp_service, mock_db, mock_config, mock_llm_service_patch):
    runner = CliRunner()
    
    # Ensure the mock supports the context manager protocol
    mock_sftp_service.__enter__ = lambda self: self
    mock_sftp_service.__exit__ = lambda self, *args: None
    
    # Set up mock data with string timestamps to match other tests
    mock_sftp_service.list_remote_files_recursive.return_value = [
        {
            "name": "file1.mkv",
            "path": "/path/to/file1.mkv",
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        }
    ]
    
    result = runner.invoke(list_remote, ["--recursive"], obj={
        "sftp": mock_sftp_service,
        "db": mock_db,
        "config": mock_config,
        "dry_run": False
    })
    assert result.exit_code == 0
    assert "file1.mkv" in result.output

def test_list_remote_populate_sftp_temp(mock_sftp_service, mock_db, mock_config, mock_llm_service_patch):
    runner = CliRunner()
    
    # Ensure the mock supports the context manager protocol
    mock_sftp_service.__enter__ = lambda self: self
    mock_sftp_service.__exit__ = lambda self, *args: None
    
    # Set up mock data with string timestamps to match other tests
    mock_sftp_service.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": "/path/to/file1.mkv",
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        }
    ]
    
    result = runner.invoke(list_remote, ["--populate-sftp-temp"], obj={
        "sftp": mock_sftp_service,
        "db": mock_db,
        "config": mock_config,
        "dry_run": False
    })
    assert result.exit_code == 0
    mock_db.insert_sftp_temp_files.assert_called_once()
    assert "Populated sftp_temp table" in result.output 