import os
import shutil
import pytest
import configparser
from pathlib import Path
from click.testing import CliRunner
from cli.main import sync2nas_cli
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import load_configuration, write_temp_config
from cli.route_files import parse_filename

@pytest.fixture
def temp_show_file(tmp_path):
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    file = incoming_dir / "Mock Show S01E03.mkv"
    file.write_text("dummy content")
    return file

@pytest.fixture
def test_config(tmp_path):
    config = configparser.ConfigParser()
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime"
    incoming_path = tmp_path / "incoming"

    anime_tv_path.mkdir()
    incoming_path.mkdir()

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

@pytest.fixture
def mock_routing(monkeypatch):
    def fake_routing(incoming_path, anime_tv_path, db, dry_run=False, auto_add=False, tmdb=None):
        print(f"fake_routing - incoming_path: {incoming_path}")
        print(f"fake_routing - anime_tv_path: {anime_tv_path}")
        return [
            {
                "original_path": os.path.join(incoming_path, "file1.mkv"),
                "routed_path": os.path.join(anime_tv_path, "Show1", "Season 01", "file1.mkv"),
                "show_name": "Show1",
                "season": "01",
                "episode": "06"
            },
            {
                "original_path": os.path.join(incoming_path, "file2.mkv"),
                "routed_path": os.path.join(anime_tv_path, "Show2", "Season 03", "file2.mkv"),
                "show_name": "Show2",
                "season": "03",
                "episode": "02"
            },
        ]

    monkeypatch.setattr("cli.route_files.file_routing", fake_routing)


@pytest.fixture
def patch_add_show(monkeypatch):
    def mock_add_show_interactively(show_name, tmdb_id, db, tmdb, anime_tv_path, dry_run, override_dir=False):
        return {
            "sys_path": f"/fake/path/{show_name}",
            "tmdb_name": show_name,
            "episode_count": 12
        }

    monkeypatch.setattr("cli.add_show.add_show_interactively", mock_add_show_interactively)


def test_route_files_basic(tmp_path, test_config_path, cli_runner, cli, mock_routing, mock_tmdb_service, mock_sftp_service):
    
    # Instantiate the CLI runner
    runner = cli_runner
    
    # Where are we running this test?
    test_path = os.path.dirname(test_config_path)
    
    # Create the config
    config_path = str(test_config_path)
    config = load_configuration(config_path)
    
    # Create all the necessary paths and directories
    os.makedirs(config["Routing"]["anime_tv_path"], exist_ok=True)
    os.makedirs(config["Transfers"]["incoming"], exist_ok=True)
    
    # Create the DB object
    db = SQLiteDBService(config["SQLite"]["db_file"])
    db.initialize()
    
    # Create the context object
    ctx = {
        "config": config,
        "db": db,
        "sftp": mock_sftp_service,
        "tmdb": mock_tmdb_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"]
    }
    
    # Run the route-files command
    result = runner.invoke(cli, ["route-files"], obj=ctx)
    
    # Assert the db was created
    assert os.path.exists(db.db_file), f"DB file was not created: {db.db_file}"
    
    # Assert the command was successful
    assert result.exit_code == 0
    
    # Assert the files were routed correctly
    assert "file1.mkv" in result.output
    assert "file2.mkv" in result.output


def test_route_files_dry_run(tmp_path, test_config_path, cli_runner, cli, mock_tmdb_service, mock_sftp_service, mock_routing):
        
    # Instantiate the CLI runner
    runner = cli_runner
    
    # Where are we running this test?
    test_path = os.path.dirname(test_config_path)
    
    # Create the config
    config_path = str(test_config_path)
    config = load_configuration(config_path)

    # Create the DB object
    db = SQLiteDBService(config["SQLite"]["db_file"])
    db.initialize()
    
    # Create the context object
    ctx = {
        "config": config,
        "db": db,
        "sftp": mock_sftp_service,
        "tmdb": mock_tmdb_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"]
    }

    # Run the route-files command
    result = runner.invoke(cli, ["route-files", "--dry-run"], obj=ctx)

    # Assert the command was successful
    assert result.exit_code == 0
    assert "file1.mkv" in result.output
    assert "file2.mkv" in result.output
    assert "[DRY RUN]" in result.output

def test_route_files_auto_add(tmp_path, test_config, mock_tmdb_service, cli_runner, cli, patch_add_show, monkeypatch, mock_sftp_service):
    config, config_path = test_config

    # Write mock file into the correct path
    incoming_path = Path(config["Transfers"]["incoming"])
    incoming_file = incoming_path / "Mock Show S01E03.mkv"
    incoming_file.write_text("dummy content")
    assert incoming_file.exists()

    db = SQLiteDBService(config["SQLite"]["db_file"])
    db.initialize()

    # Patch db.show_exists to always return False
    monkeypatch.setattr(db, "show_exists", lambda show_name: False)

    ctx = {
        "config": config,
        "db": db,
        "sftp": mock_sftp_service,
        "tmdb": mock_tmdb_service,
        "anime_tv_path": config["Routing"]["anime_tv_path"],
        "incoming_path": config["Transfers"]["incoming"],
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "route-files", "--auto-add"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "✅ Auto-added" in result.output
    assert "Mock Show" in result.output
    

# Test cases for the refactored parse_filename
test_cases = [
    ("[Group] Mock Show (2022) - 01.mkv", {"show_name": "Mock Show", "season": None, "episode": 1}),
    ("[SubsPlease] My Show - S01E05 (1080p).mkv", {"show_name": "My Show", "season": 1, "episode": 5}),
    ("My.Show.S02E09.1080p.mkv", {"show_name": "My Show", "season": 2, "episode": 9}),
    ("Cool_Show-E12.mkv", {"show_name": "Cool Show", "season": None, "episode": 12}),
    ("Title.2nd Season 07", {"show_name": "Title", "season": 2, "episode": 7}),
    ("Another Show - 103.mkv", {"show_name": "Another Show", "season": None, "episode": 103}),
    ("NoMatchHere.txt", {"show_name": "NoMatchHere", "season": None, "episode": None}),
    ("Show_with_underscores_S03E08.mkv", {"show_name": "Show with underscores", "season": 3, "episode": 8}),
    ("[FanSub]_Show.Name_03_(720p).mkv", {"show_name": "Show Name", "season": None, "episode": 3}),
]

# Create a test function for each case
@pytest.mark.parametrize("filename, expected", test_cases)
def test_parse_filename(filename, expected):
    assert parse_filename(filename) == expected