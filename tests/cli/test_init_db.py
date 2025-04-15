import gc
import sqlite3
import pytest
from click.testing import CliRunner
from cli.main import sync2nas_cli
import time

def test_init_db_creates_tables(test_config_path):
    runner = CliRunner()
    result = runner.invoke(sync2nas_cli, ["-c", str(test_config_path), "init-db"])

    assert result.exit_code == 0

    # Load config to find db path
    from utils.sync2nas_config import load_configuration
    config = load_configuration(str(test_config_path))
    db_path = config["SQLite"]["db_file"]

    # Verify expected tables exist
    # Don't use with statement for sqlite3 because we need to close the connection manually
    # and we need to wait for the database to be closed in order to cleanup 
    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';")}
        expected = {"tv_shows", "episodes", "downloaded_files", "sftp_temp_files"}
        assert expected.issubset(tables)
    finally:
        conn.close()
        gc.collect()
        time.sleep(1)
