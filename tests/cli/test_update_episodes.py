import pytest
import sqlite3
import configparser
import datetime as dt
from click.testing import CliRunner
from services.db_implementations.sqlite_implementation import SQLiteDBService
from cli.main import sync2nas_cli
from models.show import Show
from datetime import datetime
from pathlib import Path
from utils.sync2nas_config import write_temp_config, get_config_value
from tests.utils.mock_service_factory import TestConfigurationHelper
from models.episode import Episode
from models.show import Show
from services.llm_factory import create_llm_service

# -------------------------------
# Fixtures
# -------------------------------
@pytest.fixture
def test_config(tmp_path, mock_llm_service_patch):
    """
    Creates a test configuration file and directory structure for SQLite.
    """
    config = configparser.ConfigParser()
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime"
    incoming_path = tmp_path / "incoming"

    anime_tv_path.mkdir()
    incoming_path.mkdir()
    db_path.touch()

    config["Database"] = {"type": "sqlite"}
    config["SQLite"] = {"db_file": str(db_path)}
    config["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    config["Transfers"] = {"incoming": str(incoming_path)}
    config["SFTP"] = {
        "host": "localhost",
        "port": "22",
        "username": "user",
        "ssh_key_path": str(tmp_path / "dummy.key"),
        "paths": "/remote/path"
    }
    config["TMDB"] = {"api_key": "dummy"}
    config["llm"] = {"service": "ollama"}
    config["ollama"] = {
        "base_url": "http://localhost:11434",
        "model": "llama3.2:1b",
        "timeout": "30"
    }

    config_path = write_temp_config(config, tmp_path)
    return config, config_path


@pytest.fixture
def test_db(test_config, mock_llm_service_patch):
    config, _ = test_config
    db = SQLiteDBService(get_config_value(config, "sqlite", "db_file"))
    db.initialize()
    return db

@pytest.fixture
def dummy_show():
    return Show(
        sys_name="Bleach",
        sys_path="a:/anime tv/Bleach",
        tmdb_name="Bleach",
        tmdb_aliases="BLEACH 千年血战篇,BLEACH 千年血戦篇",
        tmdb_id=30985,
        tmdb_first_aired="2004-10-05T00:00:00",
        tmdb_last_aired="2024-12-29T00:00:00",
        tmdb_year=2004,
        tmdb_overview="For as long as he can remember, Ichigo Kurosaki has been able to see ghosts.",
        tmdb_season_count=2,
        tmdb_episode_count=406,
        tmdb_episode_groups='{"description": "Order of episodes according to TVDB.", "episode_count": 410, "group_count": 18, "id": "663fb548c10d4be3e80b2f6d", "name": "TVDB Order", "network": null, "type": 1}',
        tmdb_episodes_fetched_at=str(dt.datetime.now(dt.UTC)),
        tmdb_status="Returning Series",
        tmdb_external_ids='{"id": 30984, "imdb_id": "tt0434665", "tvdb_id": 74796}',
        fetched_at=str(dt.datetime.now(dt.UTC))
    )

def create_dummy_episodes():
    """
    Returns a list of fully valid Episode objects.
    """
    return [
        Episode(
            tmdb_id=30985,
            season=1,
            episode=1,
            abs_episode=1,
            episode_type="standard",
            episode_id=1001,
            air_date="2024-04-01",
            fetched_at="2024-05-09T12:00:00",
            name="Dummy Ep 1",
            overview="This is dummy episode 1."
        ),
        Episode(
            tmdb_id=30985,
            season=1,
            episode=2,
            abs_episode=2,
            episode_type="standard",
            episode_id=1002,
            air_date="2024-04-08",
            fetched_at="2024-05-09T12:00:00",
            name="Dummy Ep 2",
            overview="This is dummy episode 2."
        )
    ]

# -------------------------------
# Edge & Defensive Tests
# -------------------------------

def test_update_show_not_found(test_config, test_db, cli_runner, mock_tmdb_service, mock_sftp_service, mock_llm_service_patch):
    config, config_path = test_config
    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "--skip-validation", "update-episodes", "Missing Show"], obj={
        "config": config,
        "db": test_db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": False
    })
    assert result.exit_code == 0  # CLI returns 0 even on errors
    assert "No show found in DB for show name" in result.output

def test_tmdb_failure(monkeypatch, test_config, test_db, cli_runner, dummy_show, mock_tmdb_service, mock_sftp_service, mock_llm_service_patch):
    config, config_path = test_config
    test_db.add_show(dummy_show)

    def fail(*args, **kwargs):
        raise Exception("TMDB error")

    monkeypatch.setattr(mock_tmdb_service, "get_show_details", fail)

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "--skip-validation", "update-episodes", "Bleach"], obj={
        "config": config,
        "db": test_db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": False
    })
    assert result.exit_code == 1  # CLI returns 1 on errors
    # The error is in the exception, not the output
    assert "TMDB error" in str(result.exception)

def test_no_episodes(monkeypatch, test_config, test_db, cli_runner, dummy_show, mock_tmdb_service, mock_sftp_service, mock_llm_service_patch):
    config, config_path = test_config
    test_db.add_show(dummy_show)

    mock_tmdb_service.get_show_details.return_value = {"info": {"number_of_seasons": 2}, "episode_groups": {"results": []}}
    monkeypatch.setattr("models.episode.Episode.parse_from_tmdb", lambda *a, **k: [])

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "--skip-validation", "update-episodes", "Bleach"], obj={
        "config": config,
        "db": test_db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": False
    })

    assert result.exit_code == 0  # CLI returns 0 even on errors
    assert "Failed to fetch or update episodes for Bleach" in result.output

def test_dry_run(monkeypatch, test_config, test_db, cli_runner, dummy_show, mock_tmdb_service, mock_sftp_service, mock_llm_service_patch):
    config, config_path = test_config
    test_db.add_show(dummy_show)

    mock_tmdb_service.get_show_details.return_value = {"info": {"number_of_seasons": 2}, "episode_groups": {"results": []}}
    dummy_episodes = [dummy_show]  # just any object to avoid None
    monkeypatch.setattr("models.episode.Episode.parse_from_tmdb", lambda *a, **k: dummy_episodes)

    # Don't fail on add_episodes since dry run should skip it
    add_episodes_called = False
    def mock_add_episodes(*args, **kwargs):
        nonlocal add_episodes_called
        add_episodes_called = True
        return len(dummy_episodes)
    
    monkeypatch.setattr(test_db, "add_episodes", mock_add_episodes)

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "--skip-validation", "update-episodes", "Bleach"], obj={
        "config": config,
        "db": test_db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": True
    })

    assert result.exit_code == 0
    assert "[DRY RUN]" in result.output
    # In dry run mode, add_episodes should not be called
    assert not add_episodes_called

def test_db_failure(monkeypatch, test_config, cli_runner, mock_tmdb_service, mock_sftp_service, mock_llm_service_patch):
    config, config_path = test_config
    broken_db = SQLiteDBService(get_config_value(config, "sqlite", "db_file"))
    broken_db.initialize()
    monkeypatch.setattr(broken_db, "get_show_by_name_or_alias", lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("Mock DB error")))

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "--skip-validation", "update-episodes", "Bleach"], obj={
        "config": config,
        "db": broken_db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": False
    })
    assert result.exit_code == 1  # CLI returns 1 on errors
    # The error is in the exception, not the output
    assert "Mock DB error" in str(result.exception)

def test_unicode_show_name(test_config, test_db, cli_runner, mock_tmdb_service, mock_sftp_service, mock_llm_service_patch):
    config, config_path = test_config
    unicode_show = Show(
        sys_name="名探偵コナン",
        sys_path="/anime/名探偵コナン",
        tmdb_name="名探偵コナン",
        tmdb_aliases="Detective Conan",
        tmdb_id=9999,
        tmdb_first_aired="1996-01-01T00:00:00",
        tmdb_last_aired="2025-01-01T00:00:00",
        tmdb_year=1996,
        tmdb_overview="Japanese mystery anime",
        tmdb_season_count=30,
        tmdb_episode_count=1100,
        tmdb_episode_groups="[]",
        tmdb_episodes_fetched_at=str(dt.datetime.now(dt.UTC)),
        tmdb_status="Returning Series",
        tmdb_external_ids="{}",
        fetched_at=str(dt.datetime.now(dt.UTC))
    )
    test_db.add_show(unicode_show)

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "--skip-validation", "update-episodes", "名探偵コナン"], obj={
        "config": config,
        "db": test_db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": False
    })

    assert result.exit_code == 0
    assert "名探偵コナン" in result.output

def test_invalid_tmdb_id(test_config, cli_runner, mock_llm_service_patch):
    config, config_path = test_config
    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "update-episodes", "--tmdb-id", "abc"])
    assert result.exit_code != 0  # This should fail due to invalid argument


def test_update_by_show_name(test_config, cli_runner, cli, mock_tmdb_service, mock_sftp_service, monkeypatch, dummy_show, mock_llm_service_patch):
    """
    Validate update-episodes works when providing show_name.
    """
    config, config_path = test_config
    db = SQLiteDBService(get_config_value(config, "sqlite", "db_file"))
    db.initialize()

    # Add test show
    db.add_show(dummy_show)

    # Patch TMDB responses
    mock_tmdb_service.get_show_details.return_value = {
        "info": {"number_of_seasons": 2},
        "episode_groups": {"results": []}
    }

    # Patch episode parsing to return fake objects
    monkeypatch.setattr(
        "models.episode.Episode.parse_from_tmdb",
        lambda tmdb_id, tmdb, groups, season_count: create_dummy_episodes()
    )

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "--skip-validation", "update-episodes", "Bleach"], obj={
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,  # Not needed for this test
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": False
    })

    assert result.exit_code == 0, result.output
    assert "🎞️ Fetched 2 episodes from TMDB" in result.output
    assert "✅ 2 episodes added/updated for Bleach" in result.output


def test_update_by_tmdb_id(test_config, cli_runner, cli, mock_tmdb_service, mock_sftp_service, monkeypatch, dummy_show, mock_llm_service_patch):
    """
    Validate update-episodes works when providing tmdb_id.
    """
    config, config_path = test_config
    db = SQLiteDBService(get_config_value(config, "sqlite", "db_file"))
    db.initialize()

    # Add test show
    db.add_show(dummy_show)

    # Patch TMDB responses
    mock_tmdb_service.get_show_details.return_value = {
        "info": {"number_of_seasons": 2},
        "episode_groups": {"results": []}
    }

    # Patch episode parsing to return fake objects
    monkeypatch.setattr(
        "models.episode.Episode.parse_from_tmdb",
        lambda tmdb_id, tmdb, groups, season_count: create_dummy_episodes()
    )

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "--skip-validation", "update-episodes", "--tmdb-id", "30985"], obj={
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "llm_service": None,  # Not needed for this test
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": False
    })

    assert result.exit_code == 0, result.output
    assert "🎞️ Fetched 2 episodes from TMDB" in result.output
    assert "✅ 2 episodes added/updated for Bleach" in result.output

