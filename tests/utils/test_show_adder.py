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

def test_add_show_with_llm_success(tmp_path, mock_tmdb_service):
    """Test adding a show using LLM for show selection"""
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

    # Mock LLM service
    mock_llm_service = Mock()
    mock_llm_service.suggest_show_name.return_value = {
        "tmdb_id": 123,
        "show_name": "Mock Show",
        "confidence": 0.8
    }

    # Mock TMDB to return multiple results for LLM selection
    class MockTMDBWithResults:
        def search_show(self, name):
            return {
                "results": [
                    {"id": 123, "name": "Mock Show", "first_air_date": "2020-01-01"},
                    {"id": 456, "name": "Another Show", "first_air_date": "2020-01-01"}
                ]
            }

        def get_show_details(self, tmdb_id):
            return {
                "info": {
                    "id": tmdb_id,
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

    result = add_show_interactively(
        show_name="Mock Show",
        tmdb_id=None,
        db=db,
        tmdb=MockTMDBWithResults(),
        anime_tv_path=str(anime_tv_path),
        dry_run=False,
        use_llm=True,
        llm_service=mock_llm_service,
        max_tmdb_results=20,
        llm_confidence=0.7
    )

    shows = db.get_all_shows()
    episodes = db.get_episodes_by_show_name("Mock Show")

    assert result["tmdb_name"] == "Mock Show"
    assert result["episode_count"] == 3
    assert shows[0]["sys_name"] == "Mock Show"
    assert len(episodes) == 3
    mock_llm_service.suggest_show_name.assert_called_once()

def test_add_show_with_llm_no_results(tmp_path):
    """Test LLM branch when no TMDB search results are found"""
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

    mock_llm_service = Mock()

    class MockTMDBNoResults:
        def search_show(self, name):
            return {"results": []}

        def get_show_details(self, tmdb_id):
            return None

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError, match="No results found for show name"):
        add_show_interactively(
            show_name="Nonexistent Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBNoResults(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False,
            use_llm=True,
            llm_service=mock_llm_service
        )

def test_add_show_with_llm_no_detailed_results(tmp_path):
    """Test LLM branch when no detailed TMDB results are found"""
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

    mock_llm_service = Mock()

    class MockTMDBNoDetailedResults:
        def search_show(self, name):
            return {
                "results": [
                    {"id": 123, "name": "Mock Show", "first_air_date": "2020-01-01"}
                ]
            }

        def get_show_details(self, tmdb_id):
            return None  # No detailed results

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError, match="No detailed TMDB results for show name"):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBNoDetailedResults(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False,
            use_llm=True,
            llm_service=mock_llm_service
        )

def test_add_show_with_llm_invalid_response(tmp_path):
    """Test LLM branch when LLM returns invalid response"""
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

    # Mock LLM service returning invalid response (missing tmdb_id)
    mock_llm_service = Mock()
    mock_llm_service.suggest_show_name.return_value = {
        "show_name": "Mock Show",
        "confidence": 0.8
        # Missing tmdb_id
    }

    class MockTMDBWithResults:
        def search_show(self, name):
            return {
                "results": [
                    {"id": 123, "name": "Mock Show", "first_air_date": "2020-01-01"}
                ]
            }

        def get_show_details(self, tmdb_id):
            return {
                "info": {
                    "id": tmdb_id,
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
                    }
                ],
            }

    with pytest.raises(ValueError, match="Could not determine the best show match"):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBWithResults(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False,
            use_llm=True,
            llm_service=mock_llm_service
        )

def test_add_show_with_llm_low_confidence(tmp_path):
    """Test LLM branch when LLM confidence is below threshold"""
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

    # Mock LLM service returning low confidence
    mock_llm_service = Mock()
    mock_llm_service.suggest_show_name.return_value = {
        "tmdb_id": 123,
        "show_name": "Mock Show",
        "confidence": 0.5  # Below threshold of 0.7
    }

    class MockTMDBWithResults:
        def search_show(self, name):
            return {
                "results": [
                    {"id": 123, "name": "Mock Show", "first_air_date": "2020-01-01"}
                ]
            }

        def get_show_details(self, tmdb_id):
            return {
                "info": {
                    "id": tmdb_id,
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
                    }
                ],
            }

    with pytest.raises(ValueError, match="LLM confidence is below the threshold"):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBWithResults(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False,
            use_llm=True,
            llm_service=mock_llm_service,
            llm_confidence=0.7
        )

def test_add_show_with_llm_failed_details_retrieval(tmp_path):
    """Test LLM branch when getting show details fails after LLM selection"""
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

    # Mock LLM service
    mock_llm_service = Mock()
    mock_llm_service.suggest_show_name.return_value = {
        "tmdb_id": 123,
        "show_name": "Mock Show",
        "confidence": 0.8
    }

    class MockTMDBFailedDetails:
        def search_show(self, name):
            return {
                "results": [
                    {"id": 123, "name": "Mock Show", "first_air_date": "2020-01-01"}
                ]
            }

        def get_show_details(self, tmdb_id):
            if tmdb_id == 123:
                return None  # Failed to get details for the selected TMDB ID
            return {
                "info": {
                    "id": tmdb_id,
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

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError, match="No detailed TMDB results for show name"):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBFailedDetails(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False,
            use_llm=True,
            llm_service=mock_llm_service
        )

def test_add_show_already_exists_with_override(tmp_path, mock_tmdb_service):
    """Test adding a show that already exists but with override_dir=True"""
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

    # Try to add it again with override_dir=True (should succeed)
    result = add_show_interactively(
        show_name="Mock Show",
        tmdb_id=123,
        db=db,
        tmdb=mock_tmdb_service,
        anime_tv_path=str(anime_tv_path),
        dry_run=False,
        override_dir=True
    )

    # Should succeed and create a second show entry
    shows = db.get_all_shows()
    assert len(shows) == 2
    assert result["tmdb_name"] == "Mock Show"

def test_add_show_tmdb_id_no_details(tmp_path):
    """Test adding a show with TMDB ID but no details returned"""
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
        def get_show_details(self, tmdb_id):
            return None

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError, match="Could not retrieve show details for TMDB ID"):
        add_show_interactively(
            show_name=None,
            tmdb_id=123,
            db=db,
            tmdb=MockTMDBNoDetails(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_tmdb_id_missing_info(tmp_path):
    """Test adding a show with TMDB ID but missing info in details"""
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

    class MockTMDBMissingInfo:
        def get_show_details(self, tmdb_id):
            return {
                # Missing "info" key
                "episode_groups": {"results": []},
                "alternative_titles": {"results": []},
                "external_ids": {}
            }

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError, match="Could not retrieve show details for TMDB ID"):
        add_show_interactively(
            show_name=None,
            tmdb_id=123,
            db=db,
            tmdb=MockTMDBMissingInfo(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_show_name_no_results(tmp_path):
    """Test adding a show with show name but no search results"""
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

    class MockTMDBNoSearchResults:
        def search_show(self, name):
            return {"results": []}

        def get_show_details(self, tmdb_id):
            return None

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError, match="No results found for show name"):
        add_show_interactively(
            show_name="Nonexistent Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBNoSearchResults(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_show_name_failed_details(tmp_path):
    """Test adding a show with show name but failed to get details for first result"""
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

    class MockTMDBFailedDetails:
        def search_show(self, name):
            return {
                "results": [
                    {"id": 123, "name": "Mock Show", "first_air_date": "2020-01-01"}
                ]
            }

        def get_show_details(self, tmdb_id):
            return None  # Failed to get details

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError, match="Failed to retrieve full details for TMDB ID"):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBFailedDetails(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_show_name_missing_info(tmp_path):
    """Test adding a show with show name but missing info in details"""
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

    class MockTMDBMissingInfo:
        def search_show(self, name):
            return {
                "results": [
                    {"id": 123, "name": "Mock Show", "first_air_date": "2020-01-01"}
                ]
            }

        def get_show_details(self, tmdb_id):
            return {
                # Missing "info" key
                "episode_groups": {"results": []},
                "alternative_titles": {"results": []},
                "external_ids": {}
            }

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(ValueError, match="Failed to retrieve full details for TMDB ID"):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBMissingInfo(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )

def test_add_show_exception_handling(tmp_path):
    """Test exception handling in add_show_interactively"""
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

    # Mock TMDB to raise an exception
    class MockTMDBException:
        def search_show(self, name):
            raise Exception("TMDB API error")

        def get_show_details(self, tmdb_id):
            return None

        def get_show_season_details(self, tmdb_id, season_number):
            return None

    with pytest.raises(Exception, match="TMDB API error"):
        add_show_interactively(
            show_name="Mock Show",
            tmdb_id=None,
            db=db,
            tmdb=MockTMDBException(),
            anime_tv_path=str(anime_tv_path),
            dry_run=False
        )
