import os
import pytest
import configparser
from click.testing import CliRunner
from cli.main import sync2nas_cli
from models.show import Show
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import load_configuration
from utils.sync2nas_config import write_temp_config
from unittest.mock import patch, MagicMock
from cli.bootstrap_tv_shows import bootstrap_tv_shows
from services.llm_factory import create_llm_service


def create_temp_config(tmp_path) -> str:
    """Helper to create and return a temporary config file path."""
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
    }
    parser["TMDB"] = {"api_key": "dummy"}

    config_path = write_temp_config(parser, tmp_path)

    return str(config_path)


def test_bootstrap_tv_shows_adds_show(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)
    anime_tv_path = config["Routing"]["anime_tv_path"]
    show_name = "Mock_Show"
    os.makedirs(os.path.join(anime_tv_path, show_name), exist_ok=True)

    db = SQLiteDBService(config["SQLite"]["db_file"])
    db.initialize()

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"],
        "llm_service": create_llm_service(config),
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "bootstrap-tv-shows"], obj=obj)
    assert result.exit_code == 0
    assert "✅ Added" in result.output

    shows = db.get_all_shows()
    assert len(shows) == 1
    assert shows[0]["sys_name"] == show_name

def test_bootstrap_tv_shows_skips_existing(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)
    anime_tv_path = config["Routing"]["anime_tv_path"]
    show_name = "Mock_Show"
    sys_path = os.path.join(anime_tv_path, show_name)
    os.makedirs(sys_path, exist_ok=True)

    db = SQLiteDBService(config["SQLite"]["db_file"])
    db.initialize()

    details = mock_tmdb_service.get_show_details(123)
    show = Show.from_tmdb(details, sys_name=show_name, sys_path=sys_path)
    db.add_show(show)

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"],
        "llm_service": create_llm_service(config),
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "bootstrap-tv-shows"], obj=obj)
    assert result.exit_code == 0
    assert "⏭️ Skipped" in result.output

@pytest.mark.parametrize("folder_name", [
    "Mock Show",            # space
    "Mock-Show",            # dash
    "Mock.Show",            # dot
    "Mock+Show",            # plus sign
    "Mock_Show",            # underscore
    "Mock Show! (2020)",    # punctuation + year
    "ＭｏｃｋＳｈｏｗ",       # full-width Unicode
    "MockShow#1",           # hash symbol
    "Mock&Show",            # ampersand
])

def test_bootstrap_tv_shows_dir_names(monkeypatch, cli_runner, cli, tmp_path, folder_name, mock_tmdb_service, mock_sftp_service):
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir(parents=True, exist_ok=True)

    # Create the directory for the show
    test_dir = anime_tv_path / folder_name
    test_dir.mkdir()

    # Stub TMDB search to return mock results using the folder name
    mock_tmdb_service.search_show.side_effect = lambda query: {
        "results": [{"id": 123, "name": query, "first_air_date": "2020-01-01"}]
    }
    mock_tmdb_service.get_show_details.return_value["info"]["name"] = folder_name

    # Patch os methods to simulate real folder scanning
    monkeypatch.setattr("os.listdir", lambda _: [folder_name])
    monkeypatch.setattr("os.path.isdir", lambda x: True)

    db_path = tmp_path / "test.db"
    incoming_path = tmp_path / "incoming"
    incoming_path.mkdir()
    db_path.touch()

    parser = configparser.ConfigParser()
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(incoming_path)}
    parser["SFTP"] = {
        "host": "localhost",
        "port": "22",
        "username": "testuser",
        "ssh_key_path": str(tmp_path / "test_key"),
    }
    parser["TMDB"] = {"api_key": "test_api_key"}
    parser["llm"] = {"service": "ollama"}
    parser["ollama"] = {"model": "ollama3.2"}
    config_path = write_temp_config(parser, tmp_path)
    config = load_configuration(config_path)

    db = SQLiteDBService(str(db_path))
    db.initialize()

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": str(anime_tv_path),
        "incoming_path": str(incoming_path),
        "llm_service": create_llm_service(config),
    }

    result = cli_runner.invoke(cli, ["-c", str(config_path), "bootstrap-tv-shows"], obj=obj)

    assert result.exit_code == 0, f"CLI failed for folder: {folder_name}"
    assert "✅ Added" in result.output, f"Show not added for: {folder_name}"

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.show_exists.return_value = False
    return db

@pytest.fixture
def mock_tmdb():
    tmdb = MagicMock()
    tmdb.search_show.return_value = {
        "results": [{"id": 123, "name": "Test Show"}]
    }
    tmdb.get_show_details.return_value = {
        "info": {
            "name": "Test Show",
            "id": 123,
            "first_air_date": "2020-01-01",
            "last_air_date": "2021-01-01",
            "overview": "Test overview",
            "status": "Ended",
            "number_of_seasons": 1,
            "number_of_episodes": 10
        },
        "episode_groups": {
            "results": []
        },
        "alternative_titles": {
            "results": []
        },
        "external_ids": {
            "imdb_id": "tt1234567",
            "tvdb_id": "123456",
            "tvrage_id": "123456"
        }
    }
    return tmdb

@pytest.fixture
def mock_anime_tv_path(tmp_path):
    # Create a test directory with some folders
    os.makedirs(tmp_path / "Test Show 1")
    os.makedirs(tmp_path / "Test Show 2")
    return str(tmp_path)

@pytest.fixture
def runner():
    return CliRunner()

def test_dry_run(runner, mock_db, mock_tmdb, mock_anime_tv_path):
    """Test dry run mode where no changes are made to the database."""
    result = runner.invoke(
        bootstrap_tv_shows,
        ["--dry-run"],
        obj={"db": mock_db, "tmdb": mock_tmdb, "anime_tv_path": mock_anime_tv_path}
    )
    
    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    mock_db.add_show.assert_not_called()

def test_add_new_show(runner, mock_db, mock_tmdb, mock_anime_tv_path):
    """Test adding a new show successfully."""
    result = runner.invoke(
        bootstrap_tv_shows,
        obj={"db": mock_db, "tmdb": mock_tmdb, "anime_tv_path": mock_anime_tv_path}
    )
    
    assert result.exit_code == 0
    assert "Added: 2" in result.output
    assert mock_db.add_show.call_count == 2

def test_skip_existing_show(runner, mock_db, mock_tmdb, mock_anime_tv_path):
    """Test skipping a show that already exists in the database."""
    mock_db.show_exists.return_value = True
    
    result = runner.invoke(
        bootstrap_tv_shows,
        obj={"db": mock_db, "tmdb": mock_tmdb, "anime_tv_path": mock_anime_tv_path}
    )
    
    assert result.exit_code == 0
    assert "Skipped: 2" in result.output
    mock_db.add_show.assert_not_called()

def test_tmdb_search_failure(runner, mock_db, mock_tmdb, mock_anime_tv_path):
    """Test handling TMDB search failures."""
    mock_tmdb.search_show.return_value = {"results": []}
    
    result = runner.invoke(
        bootstrap_tv_shows,
        obj={"db": mock_db, "tmdb": mock_tmdb, "anime_tv_path": mock_anime_tv_path}
    )
    
    assert result.exit_code == 0
    assert "Failed: 2" in result.output
    mock_db.add_show.assert_not_called()

def test_tmdb_details_failure(runner, mock_db, mock_tmdb, mock_anime_tv_path):
    """Test handling TMDB details failures."""
    mock_tmdb.get_show_details.return_value = {}
    
    result = runner.invoke(
        bootstrap_tv_shows,
        obj={"db": mock_db, "tmdb": mock_tmdb, "anime_tv_path": mock_anime_tv_path}
    )
    
    assert result.exit_code == 0
    assert "Failed: 2" in result.output
    mock_db.add_show.assert_not_called()

def test_error_handling(runner, mock_db, mock_tmdb, mock_anime_tv_path):
    """Test error handling during show processing."""
    mock_tmdb.search_show.side_effect = Exception("Test error")
    
    result = runner.invoke(
        bootstrap_tv_shows,
        obj={"db": mock_db, "tmdb": mock_tmdb, "anime_tv_path": mock_anime_tv_path}
    )
    
    assert result.exit_code == 0
    assert "Failed: 2" in result.output
    mock_db.add_show.assert_not_called()

