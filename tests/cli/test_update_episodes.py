import pytest
from pathlib import Path
import configparser
from services.db_implementations.sqlite_implementation import SQLiteDBService
from cli.main import sync2nas_cli
from models.show import Show
from models.episode import Episode
from utils.sync2nas_config import write_temp_config


@pytest.fixture
def test_config(tmp_path):
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

    config["SQLite"] = {"db_file": str(db_path)}
    config["Routing"] = {"anime_tv_path": str(anime_tv_path)}
    config["Transfers"] = {"incoming": str(incoming_path)}
    config["SFTP"] = {
        "host": "localhost",
        "port": "22",
        "username": "user",
        "ssh_key_path": str(tmp_path / "dummy.key"),
        "path": "/remote/path"
    }
    config["TMDB"] = {"api_key": "dummy"}

    config_path = write_temp_config(config, tmp_path)
    return config, config_path


def create_realistic_show():
    """
    Returns a fully populated Show object compatible with DB schema.
    """
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
        tmdb_episodes_fetched_at="2025-04-13T15:48:42.154007",
        tmdb_status="Returning Series",
        tmdb_external_ids='{"id": 30984, "imdb_id": "tt0434665", "tvdb_id": 74796}',
        fetched_at="2025-04-13T15:48:42.154007"
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
            episode_type=6,
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
            episode_type=6,
            episode_id=1002,
            air_date="2024-04-08",
            fetched_at="2024-05-09T12:00:00",
            name="Dummy Ep 2",
            overview="This is dummy episode 2."
        )
    ]


def test_update_by_show_name(test_config, cli_runner, cli, mock_tmdb_service, mock_sftp_service, monkeypatch):
    """
    Validate update-episodes works when providing show_name.
    """
    config, config_path = test_config
    db = SQLiteDBService(config["SQLite"]["db_file"])
    db.initialize()

    # Add test show
    db.add_show(create_realistic_show())

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

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "update-episodes", "Bleach"], obj={
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"]
    })

    assert result.exit_code == 0, result.output
    assert "🎞️ Fetched 2 episodes from TMDB" in result.output
    assert "✅ 2 episodes added/updated for Bleach" in result.output


def test_update_by_tmdb_id(test_config, cli_runner, cli, mock_tmdb_service, mock_sftp_service, monkeypatch):
    """
    Validate update-episodes works when providing tmdb_id.
    """
    config, config_path = test_config
    db = SQLiteDBService(config["SQLite"]["db_file"])
    db.initialize()

    # Add test show
    db.add_show(create_realistic_show())

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

    result = cli_runner.invoke(sync2nas_cli, ["-c", config_path, "update-episodes", "--tmdb-id", "30985"], obj={
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"]
    })

    assert result.exit_code == 0, result.output
    assert "🎞️ Fetched 2 episodes from TMDB" in result.output
    assert "✅ 2 episodes added/updated for Bleach" in result.output
