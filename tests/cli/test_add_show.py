import os
import sys
import configparser
import pytest
from click.testing import CliRunner
from cli.main import sync2nas_cli
from models.episode import Episode
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import load_configuration, get_config_value, has_config_section
from services.llm_factory import create_llm_service
from tests.utils.mock_service_factory import TestConfigurationHelper


def test_add_show_via_name(tmp_path, test_config_path, mock_tmdb_service, mock_sftp_service, cli, cli_runner, mock_llm_service_patch):
    runner = cli_runner

    config_path = str(test_config_path)
    unique_db_path = tmp_path / "unique_test.db"
    unique_db_path.touch()

    # Load and update config with the unique DB path
    config = load_configuration(config_path)
    if not has_config_section(config, "sqlite"):
        config["sqlite"] = {}
    config["sqlite"]["db_file"] = str(unique_db_path)

    # Update the config file
    TestConfigurationHelper.update_config_file_with_normalized_data(config_path, config)

    # Create CLI context using helper
    obj = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=False,
        tmdb=mock_tmdb_service,
        sftp=mock_sftp_service
    )

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


def test_add_show_dry_run(tmp_path, test_config_path, mock_tmdb_service, mock_sftp_service, mocker, cli, cli_runner, mock_llm_service_patch):
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

    # Load and update config
    config = load_configuration(config_path)
    if not has_config_section(config, "sqlite"):
        config["sqlite"] = {}
    config["sqlite"]["db_file"] = str(unique_db_path)

    # Update the config file
    TestConfigurationHelper.update_config_file_with_normalized_data(config_path, config)

    # Create CLI context using helper with dry_run=True
    obj = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=True,
        tmdb=mock_tmdb_service,
        sftp=mock_sftp_service
    )

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
