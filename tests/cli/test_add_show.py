import os
import sys
import configparser
import pytest
from click.testing import CliRunner
from cli.main import sync2nas_cli
from models.episode import Episode
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import load_configuration
from services.llm_factory import create_llm_service


def test_add_show_via_name(tmp_path, test_config_path, mock_tmdb_service, mock_sftp_service, cli, cli_runner):
    runner = cli_runner

    config_path = str(test_config_path)
    unique_db_path = tmp_path / "unique_test.db"
    unique_db_path.touch()

    # Update config with the unique DB path
    config = load_configuration(config_path)
    config["SQLite"]["db_file"] = str(unique_db_path)

    with open(config_path, "w") as f:
        parser = configparser.ConfigParser()
        parser.read_dict(config)
        parser.write(f)

    # Initialize DB and directories
    db = SQLiteDBService(str(unique_db_path))
    db.initialize()

    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir(parents=True, exist_ok=True)

    incoming_path = tmp_path / "incoming"
    incoming_path.mkdir(parents=True, exist_ok=True)

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": str(anime_tv_path),
        "incoming_path": str(incoming_path),
        "llm_service": create_llm_service(config),
        "dry_run": False
    }

    print("Mock TMDB search_show('Mock Show'):", mock_tmdb_service.search_show("Mock Show"))

    result = runner.invoke(
        cli,
        ["add-show", "Mock Show"],
        obj=obj,
        catch_exceptions=False
    )

    if result.exit_code != 0:
        print("CLI Output:\n", result.output)
        if result.exception:
            print("Exception:\n", result.exception)
        assert False, f"CLI failed with exit code {result.exit_code}"
    assert "✅ Show added" in result.output


def test_add_show_dry_run(tmp_path, test_config_path, mock_tmdb_service, mock_sftp_service, mocker, cli, cli_runner):
    runner = cli_runner

    # Override the show name in the mock
    mock_tmdb_service.search_show.return_value = {
        "results": [{"id": 456, "name": "Mock Dry Show", "first_air_date": "2020-01-01"}]
    }
    mock_tmdb_service.get_show_details.return_value["info"]["id"] = 456

    # Patch the TMDBService in the CLI command
    mocker.patch("cli.add_show.TMDBService", return_value=mock_tmdb_service)

    config_path = str(test_config_path)
    unique_db_path = tmp_path / "unique_dry.db"

    config = load_configuration(config_path)
    config["SQLite"]["db_file"] = str(unique_db_path)

    with open(config_path, "w") as f:
        parser = configparser.ConfigParser()
        parser.read_dict(config)
        parser.write(f)

    db = SQLiteDBService(str(unique_db_path))

    # Create context object for CLI with dry_run set to True
    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": str(tmp_path / "anime_tv_path"),
        "incoming_path": str(tmp_path / "incoming"),
        "llm_service": create_llm_service(config),
        "dry_run": True  # Set dry_run to True
    }

    # Init DB
    runner.invoke(cli, ["-c", config_path, "init-db"])

    # Run CLI command without the --dry-run flag since it's already set in obj
    result = runner.invoke(cli, ["add-show", "Mock Dry Show"], obj=obj, catch_exceptions=False)

    if result.exit_code != 0:
        print("CLI Output:\n", result.output)
        if result.exception:
            print("Exception:\n", result.exception)
        assert False, f"CLI failed with exit code {result.exit_code}"
    assert "✅ DRY RUN successful" in result.output
