import os
import pytest
import datetime
import configparser
from click.testing import CliRunner
from cli.main import sync2nas_cli
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import load_configuration, write_temp_config
from pathlib import Path
from unittest.mock import patch, MagicMock
from cli.bootstrap_inventory import bootstrap_inventory
from services.llm_factory import create_llm_service

@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.obj = {
        "anime_tv_path": "/fake/path",
        "db": MagicMock(),
        "dry_run": False
    }
    return ctx

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"

@pytest.fixture
def db_service(db_path):
    db = SQLiteDBService(str(db_path))
    db.initialize()
    return db

@pytest.fixture
def temp_dir(tmp_path):
    # Create a temporary directory with test files
    d = tmp_path / "anime_tv"
    d.mkdir()
    (d / "file1.mp4").write_text("content")
    (d / "file2.txt").write_text("content")  # Invalid file
    return d

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

    return str(write_temp_config(parser, tmp_path))

def test_bootstrap_inventory_dry_run(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    anime_tv_path = config["Routing"]["anime_tv_path"]
    os.makedirs(anime_tv_path, exist_ok=True)
    (Path(anime_tv_path) / "file1.mp4").write_text("content")
    (Path(anime_tv_path) / "file2.txt").write_text("content")  # All files should be included

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": anime_tv_path,
        "incoming_path": config["Transfers"]["incoming"],
        "llm_service": create_llm_service(config),
        "dry_run": True  # Set dry_run to True
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "bootstrap-inventory"], obj=obj)

    assert result.exit_code == 0
    assert "[DRY RUN] Would insert 2 entries into anime_tv_inventory table." in result.output

def test_bootstrap_inventory_insert(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    anime_tv_path = config["Routing"]["anime_tv_path"]
    os.makedirs(anime_tv_path, exist_ok=True)
    (Path(anime_tv_path) / "file1.mp4").write_text("content")
    (Path(anime_tv_path) / "file2.txt").write_text("content")  # All files should be included

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": anime_tv_path,
        "incoming_path": config["Transfers"]["incoming"],
        "llm_service": create_llm_service(config),
        "dry_run": False
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "bootstrap-inventory"], obj=obj)

    assert result.exit_code == 0
    assert "✅ Inserted 2 files into anime_tv_inventory." in result.output

    # Verify that the files were actually inserted into the database
    inventory = db.get_inventory_files()
    assert len(inventory) == 2
    assert inventory[0]["name"] == "file1.mp4"
    assert inventory[1]["name"] == "file2.txt"

def test_bootstrap_inventory_file_filtering(tmp_path, mock_tmdb_service, mock_sftp_service, cli_runner, cli, db_service):
    config_path = create_temp_config(tmp_path)
    config = load_configuration(config_path)

    db = db_service
    db.initialize()

    anime_tv_path = config["Routing"]["anime_tv_path"]
    os.makedirs(anime_tv_path, exist_ok=True)
    (Path(anime_tv_path) / "file1.mp4").write_text("content")
    (Path(anime_tv_path) / "file2.txt").write_text("content")  # All files should be included

    obj = {
        "config": config,
        "db": db,
        "tmdb": mock_tmdb_service,
        "sftp": mock_sftp_service,
        "anime_tv_path": anime_tv_path,
        "incoming_path": config["Transfers"]["incoming"],
        "llm_service": create_llm_service(config),
        "dry_run": True  # Set dry_run to True
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "bootstrap-inventory"], obj=obj)

    assert result.exit_code == 0
    assert "[DRY RUN] Would insert 2 entries into anime_tv_inventory table." in result.output 