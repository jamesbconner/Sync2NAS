import os
import shutil
import pytest
import configparser
from pathlib import Path
from click.testing import CliRunner
from cli.main import sync2nas_cli
from services.db_implementations.sqlite_implementation import SQLiteDBService
from utils.sync2nas_config import load_configuration, write_temp_config, get_config_value
from tests.utils.mock_service_factory import TestConfigurationHelper
from utils.filename_parser import parse_filename
from services.llm_factory import create_llm_service

@pytest.fixture
def temp_show_file(tmp_path):
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    file = incoming_dir / "Mock Show S01E03.mkv"
    file.write_text("dummy content")
    return file

@pytest.fixture
def test_config(tmp_path, mock_llm_service_patch):
    config = configparser.ConfigParser()
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime"
    incoming_path = tmp_path / "incoming"

    anime_tv_path.mkdir()
    incoming_path.mkdir()

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
def mock_routing(monkeypatch):
    def fake_routing(incoming_path, anime_tv_path, db, tmdb, auto_add=False, **kwargs):
        # Get dry_run from ctx.obj if available, otherwise default to False
        dry_run = kwargs.get('dry_run', False)
        print(f"fake_routing - incoming_path: {incoming_path}")
        print(f"fake_routing - anime_tv_path: {anime_tv_path}")
        print(f"fake_routing - dry_run: {dry_run}")
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
    def mock_add_show_interactively(show_name, tmdb_id, db, tmdb, anime_tv_path, override_dir=False, dry_run=False, llm_service=None, use_llm=False, llm_confidence=0.7):
        # Get dry_run from ctx.obj if available, otherwise default to False
        return {
            "sys_path": f"/fake/path/{show_name}",
            "tmdb_name": show_name,
            "episode_count": 12
        }

    monkeypatch.setattr("cli.add_show.add_show_interactively", mock_add_show_interactively)


def test_route_files_basic(tmp_path, test_config_path, cli_runner, cli, mock_routing, mock_tmdb_service, mock_sftp_service, mock_llm_service_patch):
    
    # Instantiate the CLI runner
    runner = cli_runner
    
    # Where are we running this test?
    test_path = os.path.dirname(test_config_path)
    
    # Create the config
    config_path = str(test_config_path)
    config = load_configuration(config_path)
    
    # Create all the necessary paths and directories
    os.makedirs(get_config_value(config, "routing", "anime_tv_path"), exist_ok=True)
    os.makedirs(get_config_value(config, "transfers", "incoming"), exist_ok=True)
    
    # Create the DB object
    db = SQLiteDBService(get_config_value(config, "sqlite", "db_file"))
    db.initialize()
    
    # Create the context object
    ctx = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=False,
        db=db,
        tmdb=mock_tmdb_service,
        sftp=mock_sftp_service
    )
    
    # Run the route-files command
    result = runner.invoke(cli, ["route-files"], obj=ctx)
    
    # Assert the db was created
    assert os.path.exists(db.db_file), f"DB file was not created: {db.db_file}"
    
    # Assert the command was successful
    assert result.exit_code == 0
    
    # Assert the files were routed correctly
    assert "file1.mkv" in result.output
    assert "file2.mkv" in result.output


def test_route_files_dry_run(tmp_path, test_config_path, cli_runner, cli, mock_tmdb_service, mock_sftp_service, mock_routing, mock_llm_service_patch):
        
    # Instantiate the CLI runner
    runner = cli_runner
    
    # Where are we running this test?
    test_path = os.path.dirname(test_config_path)
    
    # Create the config
    config_path = str(test_config_path)
    config = load_configuration(config_path)

    # Create the DB object
    db = SQLiteDBService(get_config_value(config, "sqlite", "db_file"))
    db.initialize()
    
    # Create the context object
    ctx = TestConfigurationHelper.create_cli_context_from_config(
        config, 
        tmp_path, 
        dry_run=True,
        db=db,
        tmdb=mock_tmdb_service,
        sftp=mock_sftp_service
    )

    # Run the route-files command without the --dry-run flag since it's already set in obj
    result = runner.invoke(cli, ["route-files"], obj=ctx)

    # Assert the command was successful
    assert result.exit_code == 0
    assert "Dry run: Would route 2 files" in result.output
    assert "file1.mkv" in result.output
    assert "file2.mkv" in result.output

def test_route_files_auto_add(tmp_path, test_config, mock_tmdb_service, cli_runner, cli, patch_add_show, monkeypatch, mock_sftp_service, mock_llm_service_patch):
    config, config_path = test_config

    # Write mock file into the correct path
    incoming_path = Path(get_config_value(config, "transfers", "incoming"))
    incoming_file = incoming_path / "Mock Show S01E03.mkv"
    incoming_file.write_text("dummy content")
    assert incoming_file.exists()

    db = SQLiteDBService(get_config_value(config, "sqlite", "db_file"))
    db.initialize()

    # Patch db.show_exists to always return False
    monkeypatch.setattr(db, "show_exists", lambda show_name: False)

    ctx = {
        "config": config,
        "db": db,
        "sftp": mock_sftp_service,
        "tmdb": mock_tmdb_service,
        "llm_service": None,  # Not needed for this test
        "anime_tv_path": get_config_value(config, "routing", "anime_tv_path"),
        "incoming_path": get_config_value(config, "transfers", "incoming"),
        "dry_run": False
    }

    result = cli_runner.invoke(cli, ["-c", config_path, "--skip-validation", "route-files", "--auto-add"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "✅ Auto-added" in result.output
    assert "Mock Show" in result.output
    

# Test cases for the refactored parse_filename
test_cases = [
    ("[Group] Mock Show (2022) - 01.mkv", {
        "show_name": "Mock Show",
        "season": None,
        "episode": 1,
        "confidence": 0.6,
        "reasoning": "Regex pattern 4 matched"
    }),
    ("[SubsPlease] My Show - S01E05 (1080p).mkv", {
        "show_name": "My Show",
        "season": 1,
        "episode": 5,
        "confidence": 0.6,
        "reasoning": "Regex pattern 1 matched"
    }),
    ("My.Show.S02E09.1080p.mkv", {
        "show_name": "My Show",
        "season": 2,
        "episode": 9,
        "confidence": 0.6,
        "reasoning": "Regex pattern 1 matched"
    }),
    ("Cool_Show-E12.mkv", {
        "show_name": "Cool Show",
        "season": None,
        "episode": 12,
        "confidence": 0.6,
        "reasoning": "Regex pattern 3 matched"
    }),
    ("Title.2nd Season 07", {
        "show_name": "Title",
        "season": 2,
        "episode": 7,
        "confidence": 0.6,
        "reasoning": "Regex pattern 0 matched"
    }),
    ("Another Show - 103.mkv", {
        "show_name": "Another Show",
        "season": None,
        "episode": 103,
        "confidence": 0.6,
        "reasoning": "Regex pattern 4 matched"
    }),
    ("NoMatchHere.txt", {
        "show_name": "NoMatchHere",
        "season": None,
        "episode": None,
        "confidence": 0.1,
        "reasoning": "No regex pattern matched"
    }),
    ("Show_with_underscores_S03E08.mkv", {
        "show_name": "Show with underscores",
        "season": 3,
        "episode": 8,
        "confidence": 0.6,
        "reasoning": "Regex pattern 1 matched"
    }),
    ("[FanSub]_Show.Name_03_(720p).mkv", {
        "show_name": "Show Name",
        "season": None,
        "episode": 3,
        "confidence": 0.6,
        "reasoning": "Regex pattern 4 matched"
    }),
]

# Create a test function for each case
@pytest.mark.parametrize("filename, expected", test_cases)
def test_parse_filename(filename, expected, mock_llm_service_patch):
    assert parse_filename(filename) == expected