import os
import pytest
from click.testing import CliRunner
from cli.main import sync2nas_cli
from models.show import Show
from models.episode import Episode
from utils.sync2nas_config import load_configuration, write_temp_config
from services.db_service import DBService


def create_temp_config(tmp_path):
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    incoming_path = tmp_path / "incoming"

    anime_tv_path.mkdir(parents=True, exist_ok=True)
    incoming_path.mkdir(parents=True, exist_ok=True)

    config = {
        "SQLite": {"db_file": str(db_path)},
        "Routing": {"anime_tv_path": str(anime_tv_path)},
        "Transfers": {"incoming": str(incoming_path)},
        "SFTP": {
            "host": "localhost",
            "port": "22",
            "username": "testuser",
            "ssh_key_path": str(tmp_path / "test_key"),
        },
        "TMDB": {"api_key": "test_api_key"},
    }

    return write_temp_config(config, tmp_path)


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


def test_fix_show_with_tmdb_id(tmp_path, cli_runner, cli, mock_tmdb_service, mock_sftp_service, dummy_show, dummy_episodes):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = DBService(config["SQLite"]["db_file"])
    db.initialize()
    db.add_show(dummy_show)
    db.add_episodes(dummy_episodes)

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"],
    }

    result = cli_runner.invoke(
        cli,
        ["-c", config_path, "fix-show", dummy_show.sys_name, "--tmdb-id", "123"],
        obj=obj,
    )

    assert result.exit_code == 0
    assert "✅ Show corrected successfully!" in result.output

    shows = db.get_all_shows()
    assert len(shows) == 1
    assert shows[0]["tmdb_name"] == "Mock Show"

    episodes = db.get_episodes_by_show_name(shows[0]["sys_name"])
    assert len(episodes) == 3


def test_fix_show_interactive(tmp_path, cli_runner, cli, mock_tmdb_service, mock_sftp_service, dummy_show, dummy_episodes):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = DBService(config["SQLite"]["db_file"])
    db.initialize()
    db.add_show(dummy_show)
    db.add_episodes(dummy_episodes)

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"],
    }

    result = cli_runner.invoke(
        cli,
        ["-c", config_path, "fix-show", dummy_show.sys_name],
        input="0\n",  # Select the first TMDB search result
        obj=obj,
    )

    assert result.exit_code == 0
    assert "✅ Show corrected successfully!" in result.output

    shows = db.get_all_shows()
    assert len(shows) == 1
    assert shows[0]["tmdb_name"] == "Mock Show"

    episodes = db.get_episodes_by_show_name(shows[0]["sys_name"])
    assert len(episodes) == 3
