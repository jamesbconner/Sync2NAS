import os
import pytest
import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from models.episode import Episode
from models.show import Show
from services.db_factory import create_db_service
from services.tmdb_service import TMDBService
from utils.show_adder import add_show_interactively
from utils.sync2nas_config import write_temp_config, load_configuration
import configparser

@pytest.fixture
def mock_db():
    return Mock(spec=create_db_service)

@pytest.fixture
def mock_tmdb():
    return Mock(spec=TMDBService)

@pytest.fixture
def mock_details():
    return {
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

@pytest.fixture
def mock_tmdb_service(mock_details):
    class MockTMDB:
        def search_show(self, name):
            return {"results": [{"id": 123, "name": name, "first_air_date": "2020-01-01"}]}

        def get_show_details(self, tmdb_id):
            return mock_details

        def get_show_season_details(self, tmdb_id, season_number):
            return {
                "id": season_number,
                "air_date": "2020-01-01",
                "season_number": season_number,
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
                    },
                ],
            }

    return MockTMDB()

def test_add_show_interactively(tmp_path, mock_tmdb_service):
    """Test adding a show with show name"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    db_path.touch()
    
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    
    db = create_db_service(config)
    db.initialize()

    result = add_show_interactively(
        show_name="Mock Show",
        tmdb_id=None,
        db=db,
        tmdb=mock_tmdb_service,
        anime_tv_path=str(anime_tv_path),
        dry_run=False
    )

    shows = db.get_all_shows()
    episodes = db.get_episodes_by_show_name("Mock Show")

    assert result["tmdb_name"] == "Mock Show"
    assert result["episode_count"] == 3
    assert shows[0]["sys_name"] == "Mock Show"
    assert len(episodes) == 3

def test_add_show_interactively_dry_run(tmp_path, mock_tmdb_service):
    """Test dry run mode"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    result = add_show_interactively(
        show_name="Mock Show",
        tmdb_id=None,
        db=db,
        tmdb=mock_tmdb_service,
        anime_tv_path=str(anime_tv_path),
        dry_run=True
    )

    assert result["tmdb_name"] == "Mock Show"
    assert result["episode_count"] == 3
    assert db.get_all_shows() == []

def test_add_show_with_tmdb_id(tmp_path, mock_tmdb_service):
    """Test adding a show with TMDB ID"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    result = add_show_interactively(
        show_name=None,
        tmdb_id=123,
        db=db,
        tmdb=mock_tmdb_service,
        anime_tv_path=str(anime_tv_path),
        dry_run=False
    )

    shows = db.get_all_shows()
    episodes = db.get_episodes_by_show_name("Mock Show")

    assert result["tmdb_name"] == "Mock Show"
    assert result["episode_count"] == 3
    assert shows[0]["sys_name"] == "Mock Show"
    assert len(episodes) == 3

def test_add_show_with_override_dir(tmp_path, mock_tmdb_service):
    """Test adding a show with override_dir flag"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    result = add_show_interactively(
        show_name="Custom Show Name",
        tmdb_id=123,
        db=db,
        tmdb=mock_tmdb_service,
        anime_tv_path=str(anime_tv_path),
        dry_run=False,
        override_dir=True
    )

    shows = db.get_all_shows()
    episodes = db.get_episodes_by_show_name("Custom Show Name")

    assert result["tmdb_name"] == "Mock Show"
    assert result["episode_count"] == 3
    assert shows[0]["sys_name"] == "Custom Show Name"
    assert len(episodes) == 3

def test_add_show_already_exists(tmp_path, mock_tmdb_service):
    """Test adding a show that already exists"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    # First add the show
    add_show_interactively(
        show_name="Mock Show",
        tmdb_id=None,
        db=db,
        tmdb=mock_tmdb_service,
        anime_tv_path=str(anime_tv_path),
        dry_run=False
    )

    # Try to add it again
    with pytest.raises(FileExistsError):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=mock_tmdb_service,
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_no_tmdb_details(tmp_path):
    """Test adding a show when TMDB details are not found"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    class MockTMDBNoDetails:
        def search_show(self, name):
            return {"results": [{"id": 123, "name": name, "first_air_date": "2020-01-01"}]}

        def get_show_details(self, tmdb_id):
            return None

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBNoDetails(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_no_search_results(tmp_path):
    """Test adding a show when no search results are found"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    class MockTMDBNoResults:
        def search_show(self, name):
            return {"results": []}

        def get_show_details(self, tmdb_id):
            return None

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError):
        add_show_interactively(
            show_name="Nonexistent Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBNoResults(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_no_show_name_or_tmdb_id(tmp_path, mock_tmdb_service):
    """Test adding a show with neither show name nor TMDB ID"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    with pytest.raises(ValueError):
        add_show_interactively(
            show_name=None,
            tmdb_id=None,
            db=db,
            tmdb=mock_tmdb_service,
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_directory_creation_error(tmp_path, mock_tmdb_service):
    """Test error handling when directory creation fails"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    with patch('os.makedirs', side_effect=OSError("Permission denied")):
        with pytest.raises(OSError):
            add_show_interactively(
                show_name="Mock Show",
                tmdb_id=None,
                db=db,
                tmdb=mock_tmdb_service,
                anime_tv_path=str(anime_tv_path),
                dry_run=False
            )

        # Verify database operations were not attempted
        assert len(db.get_all_shows()) == 0

def test_add_show_database_error(tmp_path, mock_tmdb_service):
    """Test error handling when database operations fail"""
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": str(db_path)}
    parser["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
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
    db = create_db_service(config)
    db.initialize()

    # Mock the database to raise an error on add_show
    with patch.object(db, 'add_show', side_effect=Exception("Database error")):
        with pytest.raises(Exception):
            add_show_interactively(
                show_name="Mock Show",
                tmdb_id=None,
                db=db,
                tmdb=mock_tmdb_service,
                anime_tv_path=str(anime_tv_path),
                dry_run=False
            )

        # Verify show was not added
        assert len(db.get_all_shows()) == 0
