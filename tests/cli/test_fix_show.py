import os
import pytest
from click.testing import CliRunner
from click import Context
from cli.main import sync2nas_cli
from models.show import Show
from models.episode import Episode
from utils.sync2nas_config import load_configuration, write_temp_config, get_config_value
from tests.utils.mock_service_factory import TestConfigurationHelper
from services.db_implementations.sqlite_implementation import SQLiteDBService
from services.tmdb_service import TMDBService
from cli.fix_show import fix_show
from unittest.mock import Mock, patch
from datetime import datetime
from services.llm_factory import create_llm_service
import configparser


def create_temp_config(tmp_path):
    config = configparser.ConfigParser()
    db_path = tmp_path / "test.db"
    
    config["Database"] = {"type": "sqlite"}
    config["SQLite"] = {"db_file": str(db_path)}
    config["Routing"] = {"anime_tv_path": str(tmp_path / "anime_tv")}
    config["Transfers"] = {"incoming": str(tmp_path / "incoming")}
    config["SFTP"] = {
        "host": "localhost",
        "port": "22",
        "username": "testuser",
        "ssh_key_path": str(tmp_path / "test_key"),
        "paths": "/remote"
    }
    config["TMDB"] = {"api_key": "test_api_key"}
    config["llm"] = {"service": "ollama"}
    config["ollama"] = {"model": "qwen3:14b"}
    
    config_path = tmp_path / "test_config.ini"
    with config_path.open("w") as config_file:
        config.write(config_file)
    
    return config_path


@pytest.fixture
def dummy_show(tmp_path):
    show_path = tmp_path / "anime_tv_path" / "Mock_Show"
    show_path.mkdir(parents=True, exist_ok=True)

    return Show(
        tmdb_id=123,
        sys_name="Mock_Show",
        sys_path=str(show_path),
        tmdb_name="Wrong Show",
        tmdb_aliases="",
        tmdb_first_aired=None,
        tmdb_last_aired=None,
        tmdb_year=2020,
        tmdb_overview="Bad metadata",
        tmdb_season_count=1,
        tmdb_episode_count=1,
        tmdb_episode_groups="[]",
        tmdb_episodes_fetched_at=None,
        tmdb_status="Ended",
        tmdb_external_ids={},
        fetched_at=None,
    )


@pytest.fixture
def dummy_episodes():
    return [
        Episode(
            tmdb_id=123,
            season=1,
            episode=i + 1,
            abs_episode=i + 1,
            episode_type="standard",
            episode_id=1000 + i,
            air_date=None,
            fetched_at=None,
            name=f"Ep {i+1}",
            overview=f"Overview {i+1}",
        )
        for i in range(2)
    ]


@pytest.fixture
def mock_db():
    return Mock(spec=SQLiteDBService)


@pytest.fixture
def mock_tmdb():
    return Mock(spec=TMDBService)


@pytest.fixture
def mock_show_details():
    return {
        "info": {
            "id": 123,
            "name": "Test Show",
            "first_air_date": "2020-01-01",
            "number_of_seasons": 1,
            "number_of_episodes": 3,
            "overview": "Test Overview",
            "status": "Ended"
        },
        "episode_groups": {"results": []},
        "alternative_titles": {
            "results": [
                {"title": "Test Show Alternative", "type": "alternative"}
            ]
        },
        "external_ids": {
            "imdb_id": "tt1234567",
            "tvdb_id": "123456",
            "tvrage_id": None
        }
    }


@pytest.fixture
def mock_search_results():
    return {
        "results": [
            {
                "id": 123,
                "name": "Test Show",
                "first_air_date": "2020-01-01",
                "overview": "Test Overview"
            }
        ]
    }


@pytest.fixture
def mock_episodes():
    return [
        Episode(
            tmdb_id=123,
            season=1,
            episode=1,
            abs_episode=1,
            episode_type="standard",
            episode_id=1001,
            air_date="2020-01-01",
            name="Episode 1",
            overview="Overview 1",
            fetched_at=datetime.now()
        ),
        Episode(
            tmdb_id=123,
            season=1,
            episode=2,
            abs_episode=2,
            episode_type="standard",
            episode_id=1002,
            air_date="2020-01-02",
            name="Episode 2",
            overview="Overview 2",
            fetched_at=datetime.now()
        ),
        Episode(
            tmdb_id=123,
            season=1,
            episode=3,
            abs_episode=3,
            episode_type="standard",
            episode_id=1003,
            air_date="2020-01-03",
            name="Episode 3",
            overview="Overview 3",
            fetched_at=datetime.now()
        )
    ]


def create_click_context(mock_db, mock_tmdb, tmp_path):
    """Helper function to create a proper Click context"""
    ctx = Context(fix_show)
    parser = configparser.ConfigParser()
    parser["Database"] = {"type": "sqlite"}
    parser["SQLite"] = {"db_file": "test.db"}
    parser["Routing"] = {"anime_tv_path": str(tmp_path / "anime_tv_path")}
    parser["Transfers"] = {"incoming": str(tmp_path / "incoming")}
    parser["SFTP"] = {
        "host": "localhost",
        "port": "22",
        "username": "testuser",
        "ssh_key_path": str(tmp_path / "test_key"),
    }
    parser["TMDB"] = {"api_key": "test_api_key"}
    parser["llm"] = {"service": "ollama"}
    parser["ollama"] = {"model": "qwen3:14b"}
    config_path = write_temp_config(parser, tmp_path)
    config = load_configuration(config_path)
    ctx.obj = {
        "config": config,
        "db": mock_db,
        "tmdb": mock_tmdb,
        "anime_tv_path": str(tmp_path / "anime_tv_path"),
        "incoming_path": str(tmp_path / "incoming"),
        "dry_run": False  # Add dry_run key
    }
    return ctx


def test_fix_show_with_tmdb_id(tmp_path, mock_db, mock_tmdb, mock_show_details, mock_episodes, mock_llm_service_patch):
    """Test fixing a show using a TMDB ID override"""
    # Setup mock database
    mock_db.get_all_shows.return_value = [
        {"sys_name": "Test Show", "tmdb_id": 456, "sys_path": "/test/path"}
    ]
    mock_tmdb.get_show_details.return_value = mock_show_details
    with patch('models.episode.Episode.parse_from_tmdb', return_value=mock_episodes):
        # Setup context
        ctx = create_click_context(mock_db, mock_tmdb, tmp_path)

        # Run command
        runner = CliRunner()
        result = runner.invoke(fix_show, ["Test Show", "--tmdb-id", "123"], obj=ctx.obj)

        # Verify
        assert result.exit_code == 0
        mock_db.delete_show_and_episodes.assert_called_once_with(456)
        mock_db.add_show.assert_called_once()
        mock_db.add_episodes.assert_called_once_with(mock_episodes)


def test_fix_show_interactive(tmp_path, mock_db, mock_tmdb, mock_show_details, mock_search_results, mock_episodes, mock_llm_service_patch):
    """Test fixing a show with interactive TMDB search"""
    # Setup mock database
    mock_db.get_all_shows.return_value = [
        {"sys_name": "Test Show", "tmdb_id": 456, "sys_path": "/test/path"}
    ]
    mock_tmdb.search_show.return_value = mock_search_results
    mock_tmdb.get_show_details.return_value = mock_show_details
    with patch('models.episode.Episode.parse_from_tmdb', return_value=mock_episodes):
        # Setup context
        ctx = create_click_context(mock_db, mock_tmdb, tmp_path)

        # Run command with input
        runner = CliRunner()
        result = runner.invoke(fix_show, ["Test Show"], input="0\n", obj=ctx.obj)

        # Verify
        assert result.exit_code == 0
        mock_db.delete_show_and_episodes.assert_called_once_with(456)
        mock_db.add_show.assert_called_once()
        mock_db.add_episodes.assert_called_once_with(mock_episodes)


def test_fix_show_dry_run(tmp_path, mock_db, mock_tmdb, mock_show_details, mock_episodes, mock_llm_service_patch):
    """Test dry run mode"""
    # Setup mock database
    mock_db.get_all_shows.return_value = [
        {"sys_name": "Test Show", "tmdb_id": 456, "sys_path": "/test/path"}
    ]
    mock_tmdb.get_show_details.return_value = mock_show_details
    with patch('models.episode.Episode.parse_from_tmdb', return_value=mock_episodes):
        # Setup context with dry_run flag
        ctx = create_click_context(mock_db, mock_tmdb, tmp_path)
        ctx.obj["dry_run"] = True

        # Run command
        runner = CliRunner()
        result = runner.invoke(fix_show, ["Test Show", "--tmdb-id", "123"], obj=ctx.obj)

        # Verify
        assert result.exit_code == 0
        mock_db.delete_show_and_episodes.assert_not_called()
        mock_db.add_show.assert_not_called()
        mock_db.add_episodes.assert_not_called()
        assert "DRY RUN" in result.output


def test_fix_show_not_found(tmp_path, mock_db, mock_llm_service_patch):
    """Test when show is not found in database"""
    # Setup mock database
    mock_db.get_all_shows.return_value = []

    # Setup context
    ctx = create_click_context(mock_db, Mock(), tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(fix_show, ["Nonexistent Show"], obj=ctx.obj)

    # Verify
    assert result.exit_code == 0
    assert "No show found in database" in result.output
    mock_db.delete_show_and_episodes.assert_not_called()


def test_fix_show_no_tmdb_results(tmp_path, mock_db, mock_tmdb, mock_llm_service_patch):
    """Test when no TMDB results are found"""
    # Setup mock database
    mock_db.get_all_shows.return_value = [
        {"sys_name": "Test Show", "tmdb_id": 456, "sys_path": "/test/path"}
    ]
    mock_tmdb.search_show.return_value = {"results": []}

    # Setup context
    ctx = create_click_context(mock_db, mock_tmdb, tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(fix_show, ["Test Show"], obj=ctx.obj)

    # Verify
    assert result.exit_code == 0
    assert "No TMDB results found" in result.output
    mock_db.delete_show_and_episodes.assert_not_called()


def test_fix_show_invalid_index(tmp_path, mock_db, mock_tmdb, mock_search_results, mock_llm_service_patch):
    """Test when invalid index is selected"""
    # Setup mock database
    mock_db.get_all_shows.return_value = [
        {"sys_name": "Test Show", "tmdb_id": 456, "sys_path": "/test/path"}
    ]
    mock_tmdb.search_show.return_value = mock_search_results

    # Setup context
    ctx = create_click_context(mock_db, mock_tmdb, tmp_path)

    # Run command with invalid index
    runner = CliRunner()
    result = runner.invoke(fix_show, ["Test Show"], input="999\n", obj=ctx.obj)

    # Verify
    assert result.exit_code == 0
    assert "Invalid index selected" in result.output
    mock_db.delete_show_and_episodes.assert_not_called()


def test_fix_show_tmdb_error(tmp_path, mock_db, mock_tmdb, mock_show_details, mock_llm_service_patch):
    """Test when TMDB service returns an error"""
    # Setup mock database
    mock_db.get_all_shows.return_value = [
        {"sys_name": "Test Show", "tmdb_id": 456, "sys_path": "/test/path"}
    ]
    mock_tmdb.get_show_details.return_value = None

    # Setup context
    ctx = create_click_context(mock_db, mock_tmdb, tmp_path)

    # Run command
    runner = CliRunner()
    result = runner.invoke(fix_show, ["Test Show", "--tmdb-id", "123"], obj=ctx.obj)

    # Verify
    assert result.exit_code == 0
    assert "Could not fetch details for TMDB ID" in result.output
    mock_db.delete_show_and_episodes.assert_not_called()


def test_fix_show_database_error(tmp_path, mock_db, mock_tmdb, mock_show_details, mock_episodes, mock_llm_service_patch):
    """Test when database operations fail"""
    # Setup mock database
    mock_db.get_all_shows.return_value = [
        {"sys_name": "Test Show", "tmdb_id": 456, "sys_path": "/test/path"}
    ]
    mock_tmdb.get_show_details.return_value = mock_show_details
    with patch('models.episode.Episode.parse_from_tmdb', return_value=mock_episodes):
        mock_db.delete_show_and_episodes.side_effect = Exception("Database error")

        # Setup context
        ctx = create_click_context(mock_db, mock_tmdb, tmp_path)

        # Run command
        runner = CliRunner()
        result = runner.invoke(fix_show, ["Test Show", "--tmdb-id", "123"], obj=ctx.obj)

        # Verify
        assert result.exit_code == 0
        assert "Error correcting show" in result.output
        mock_db.add_show.assert_not_called()
        mock_db.add_episodes.assert_not_called()

