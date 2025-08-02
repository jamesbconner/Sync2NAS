import os
import sys
import time
import shutil
import tempfile
import pytest
import configparser
import sqlite3
from pathlib import Path
from click.testing import CliRunner

# Add project root to sys.path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.sync2nas_config import load_configuration
from services.db_factory import create_db_service
from services.tmdb_service import TMDBService
from services.sftp_service import SFTPService
from cli.main import sync2nas_cli

# ────────────────────────────────────────────────
# CONFIGURATION FIXTURES
# ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_config_path():
    """Create a temporary configuration file for Sync2NAS tests."""
    temp_dir = Path(tempfile.gettempdir()) / "test_sync2nas"
    temp_dir.mkdir(parents=True, exist_ok=True)

    config_path = temp_dir / "test_sync2nas_config.ini"
    config = configparser.ConfigParser()

    config["Database"] = {"type": "sqlite"}
    config["SQLite"] = {"db_file": str(temp_dir / "test.db")}
    config["Routing"] = {"anime_tv_path": str(temp_dir / "anime_tv_path")}
    config["Transfers"] = {"incoming": str(temp_dir / "incoming")}
    config["SFTP"] = {
        "host": "localhost",
        "port": "22",
        "username": "testuser",
        "ssh_key_path": str(temp_dir / "test_key"),
        "paths": "/remote"
    }
    config["TMDB"] = {"api_key": "test_api_key"}
    config["llm"] = {"service": "ollama"}
    config["ollama"] = {"model": "llama3.2"}

    with config_path.open("w") as config_file:
        config.write(config_file)

    return config_path


@pytest.fixture(scope="session")
def config(test_config_path):
    """Load the configuration from the test config path."""
    return load_configuration(str(test_config_path))


# ────────────────────────────────────────────────
# DATABASE FIXTURES
# ────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_service(config):
    """Return a database service initialized with the test database."""
    db = create_db_service(config)
    db.initialize()
    return db


@pytest.fixture(scope="function")
def initialized_db(db_service):
    """Alias for an initialized DBService (backwards-compatible)."""
    return db_service


# ────────────────────────────────────────────────
# MOCK FIXTURES
# ────────────────────────────────────────────────

@pytest.fixture(scope="function")
def mock_tmdb_service(mocker):
    """Mocked TMDBService instance with stubbed return values."""
    mock = mocker.Mock(spec=TMDBService)

    mock.search_show.return_value = {
        "results": [
            {"id": 123, "name": "Mock Show", "first_air_date": "2020-01-01"}
        ]
    }

    mock.get_show_details.return_value = {
        "info": {
            "id": 123,
            "name": "Mock Show",
            "first_air_date": "2020-01-01",
            "number_of_seasons": 1,
            "number_of_episodes": 3,
            "overview": "Test Overview"
        },
        "episode_groups": {"results": []},
        "alternative_titles": {"results": []},
        "external_ids": {}
    }

    mock.get_show_season_details.return_value = {
        "id": 1,
        "air_date": "2020-01-01",
        "season_number": 1,
        "episodes": [
            {
                "episode_number": 1,
                "id": 1001,
                "air_date": "2020-01-01",
                "name": "Episode 1",
                "overview": "Overview 1",
            },
            {
                "episode_number": 2,
                "id": 1002,
                "air_date": "2020-01-08",
                "name": "Episode 2",
                "overview": "Overview 2",
            },
            {
                "episode_number": 3,
                "id": 1003,
                "air_date": "2020-01-15",
                "name": "Episode 3",
                "overview": "Overview 3",
            }
        ]
    }

    mock.get_show_episode_details.side_effect = lambda id, season, episode: {
        "episode_number": episode,
        "id": 1000 + episode,
        "air_date": f"2020-01-{1 + 7 * (episode - 1):02d}",
        "name": f"Episode {episode}",
        "overview": f"Overview {episode}",
        "season_number": season,
        "show_id": id
    }

    return mock

@pytest.fixture(scope="function")
def mock_sftp_service(mocker):
    """Mocked SFTPService instance with stubbed return values."""
    # Create a MagicMock with the spec
    mock = mocker.MagicMock(spec=SFTPService)
    
    # Set up the required attributes that the code accesses
    mock.host = "localhost"
    mock.port = 22
    mock.username = "testuser"
    mock.ssh_key_path = "/tmp/test_key"
    mock.llm_service = None
    
    mock.list_remote_dir.return_value = [
        {
            "name": "file1.mkv",
            "path": "/path/to/file1.mkv",
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        },
        {
            "name": "file2.mkv",
            "path": "/path/to/file2.mkv",
            "size": 200,
            "modified_time": "2020-01-01 12:00:01",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:01"
        }
    ]
    
    mock.list_remote_files_recursive.return_value = [
        {
            "name": "file1.mkv",
            "path": "/path/to/file1.mkv",
            "size": 100,
            "modified_time": "2020-01-01 12:00:00",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:00"
        },
        {
            "name": "file2.mkv",
            "path": "/path/to/file2.mkv",
            "size": 200,
            "modified_time": "2020-01-01 12:00:01",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:01"
        },
        {
            "name": "subdir/file3.mkv",
            "path": "/path/to/subdir/file3.mkv",
            "size": 300,
            "modified_time": "2020-01-01 12:00:02",
            "is_dir": False,
            "fetched_at": "2020-01-01 12:00:02"
        }
    ]
    
    mock.download_file.return_value = True
    mock.download_dir.return_value = False
    
    # Set up context manager behavior
    mock.__enter__.return_value = mock
    
    return mock

# ────────────────────────────────────────────────
# CLI FIXTURES
# ────────────────────────────────────────────────

@pytest.fixture
def cli_runner():
    """Provide a Click test runner."""
    return CliRunner()


@pytest.fixture
def cli():
    """Provide a Sync2NAS CLI instance."""
    return sync2nas_cli


# ────────────────────────────────────────────────
# CLEANUP FIXTURES
# ────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_env(request, test_config_path):
    """Clean up the temporary environment after the test session."""
    temp_root = Path(test_config_path).parent

    def cleanup():
        max_retries = 5
        delay = 1
        for attempt in range(max_retries):
            try:
                if temp_root.exists():
                    shutil.rmtree(temp_root)
                break
            except PermissionError as e:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 1.5  # Exponential backoff
                else:
                    print(f"\nFailed to delete temp directory after {max_retries} attempts.")
                    raise e

    request.addfinalizer(cleanup)