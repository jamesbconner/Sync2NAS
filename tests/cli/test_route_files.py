import os
import shutil
import pytest
from pathlib import Path
from click.testing import CliRunner
from cli.main import sync2nas_cli
from services.db_service import DBService
from utils.sync2nas_config import load_configuration, write_temp_config



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
    db = DBService(config["SQLite"]["db_file"])
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
    db = DBService(config["SQLite"]["db_file"])
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

def test_route_files_auto_add(tmp_path, test_config_path, cli_runner, cli, mock_tmdb_service, mock_sftp_service):

    # Load and prepare config
    config = load_configuration(str(test_config_path))
    anime_tv_path = Path(config["Routing"]["anime_tv_path"])
    incoming_path = Path(config["Transfers"]["incoming"])
    anime_tv_path.mkdir(parents=True, exist_ok=True)
    incoming_path.mkdir(parents=True, exist_ok=True)

    # Create an incoming file with a name that will trigger TMDB lookup
    test_filename = "Mock Show.S01E03.mkv"
    incoming_file = incoming_path / test_filename
    incoming_file.write_text("test content")
    assert os.path.exists(incoming_file), "Incoming file should have been created"

    # Set up DB
    db = DBService(config["SQLite"]["db_file"])
    db.initialize()

    # Construct context
    ctx = {
        "config": config,
        "db": db,
        "sftp": mock_sftp_service,
        "tmdb": mock_tmdb_service,
        "anime_tv_path": str(anime_tv_path),
        "incoming_path": str(incoming_path),
    }

    # Run CLI with --auto-add
    result = cli_runner.invoke(cli, ["route-files", "--auto-add"], obj=ctx)
    output = result.output

    # Assertions
    assert os.path.exists(db.db_file), "DB file should have been created"
    assert result.exit_code == 0, f"CLI exited with error: {output}"
    assert "Added new show" in output or "✅" in output, "Should indicate show was added"
    assert test_filename in output, "File should appear in output as routed"

    # DB assertions
    show = db.get_show_by_name_or_alias("Mock Show")
    assert show, "Show should have been inserted into DB"
    episodes = db.get_episodes_by_show_name("Mock Show")
    assert episodes, "Episodes should have been populated for the show"

    # Filesystem assertion
    routed_path = Path(show["sys_path"]) / "Season 01" / test_filename
    assert routed_path.exists(), f"File should have been moved to: {routed_path}"
