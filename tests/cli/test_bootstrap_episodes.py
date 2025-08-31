import os
import pytest
import datetime
import configparser
from click.testing import CliRunner
from cli.main import sync2nas_cli
from models.show import Show
from models.episode import Episode
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import load_configuration, write_temp_config, get_config_value
from tests.utils.mock_service_factory import TestConfigurationHelper
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
    }
    parser["TMDB"] = {"api_key": "dummy"}
    parser["llm"] = {"service": "ollama"}
    parser["ollama"] = {
        "base_url": "http://localhost:11434",
        "model": "llama3.2:1b",
        "timeout": "30"
    }

    return str(write_temp_config(parser, tmp_path))


def test_bootstrap_episodes_adds_records(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, mock_llm_service_patch):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db_path = get_config_value(config, "sqlite", "db_file")
    db = SQLiteDBService(db_path)
    db.initialize()

    anime_tv_path = get_config_value(config, "routing", "anime_tv_path")
    show_name = "Mock_Show"
    sys_path = os.path.join(anime_tv_path, show_name)
    os.makedirs(sys_path, exist_ok=True)

    details = mock_tmdb_service.get_show_details(123)
    show = Show.from_tmdb(details, sys_name=show_name, sys_path=sys_path)
    db.add_show(show)

    obj = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=False,
        db=db,
        tmdb=mock_tmdb_service,
        sftp=mock_sftp_service
    )

    result = cli_runner.invoke(cli, ["-c", config_path, "bootstrap-episodes"], obj=obj)

    assert result.exit_code == 0
    assert "✅ Added" in result.output

    episodes = db.get_episodes_by_show_name(show.sys_name)
    assert len(episodes) == 3



def test_bootstrap_episodes_skips_existing(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, mock_llm_service_patch):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db_path = get_config_value(config, "sqlite", "db_file")
    db = SQLiteDBService(db_path)
    db.initialize()

    anime_tv_path = get_config_value(config, "routing", "anime_tv_path")
    show_name = "Mock_Show"
    sys_path = os.path.join(anime_tv_path, show_name)
    os.makedirs(sys_path, exist_ok=True)

    details = mock_tmdb_service.get_show_details(123)
    show = Show.from_tmdb(details, sys_name=show_name, sys_path=sys_path)
    db.add_show(show)

    episode = Episode(
        tmdb_id=show.tmdb_id,
        season=1,
        episode=1,
        abs_episode=1,
        episode_type="standard",
        episode_id=999,
        air_date=datetime.datetime(2020, 1, 1),
        fetched_at=datetime.datetime.now(),
        name="Mock Episode",
        overview="Test"
    )
    db.add_episode(episode)

    obj = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=False,
        db=db,
        tmdb=mock_tmdb_service,
        sftp=mock_sftp_service
    )

    result = cli_runner.invoke(cli, ["-c", config_path, "bootstrap-episodes"], obj=obj)

    assert result.exit_code == 0
    assert "⏭️ Skipped" in result.output

