# tests/services/test_db_service.py

import pytest
import os
import datetime
import sqlite3

from services.db_factory import create_db_service
from models.show import Show
from models.episode import Episode


# ────────────────────────────────────────────────
# SHOW MANAGEMENT TESTS
# ────────────────────────────────────────────────

def test_add_show_and_query(db_service):
    show = Show(
        sys_name="TestShow",
        sys_path="/fake/path/TestShow",
        tmdb_name="Test Show",
        tmdb_aliases="",
        tmdb_id=1,
        tmdb_first_aired=datetime.datetime.now(),
        tmdb_last_aired=datetime.datetime.now(),
        tmdb_year=2020,
        tmdb_overview="Overview",
        tmdb_season_count=1,
        tmdb_episode_count=3,
        tmdb_episode_groups="[]",
        tmdb_episodes_fetched_at=datetime.datetime.now(),
        tmdb_status="Ended",
        tmdb_external_ids="{}",
        fetched_at=datetime.datetime.now()
    )
    db_service.add_show(show)
    assert db_service.show_exists("TestShow")

def test_show_exists_alias_match(db_service):
    class FakeShow:
        tmdb_name = "The Real Show"
        def to_db_tuple(self):
            return (
                "Test Show", "/fake/path", "The Real Show", "alias1, alias2", 101,
                None, None, None, None, 1, 10, None, None, "Ended", None, None
            )
    db_service.add_show(FakeShow())
    assert db_service.show_exists("alias2")

def test_get_show_by_sys_name(db_service):
    show = Show(
        sys_name="TestShow",
        sys_path="/fake/path/TestShow",
        tmdb_name="Test Show",
        tmdb_aliases="",
        tmdb_id=1,
        tmdb_first_aired=datetime.datetime.now(),
        tmdb_last_aired=datetime.datetime.now(),
        tmdb_year=2020,
        tmdb_overview="Overview",
        tmdb_season_count=1,
        tmdb_episode_count=3,
        tmdb_episode_groups="[]",
        tmdb_episodes_fetched_at=datetime.datetime.now(),
        tmdb_status="Ended",
        tmdb_external_ids="{}",
        fetched_at=datetime.datetime.now()
    )
    db_service.add_show(show)
    result = db_service.get_show_by_sys_name("TestShow")
    assert result["sys_name"] == "TestShow"

def test_get_show_by_alias(db_service):
    # Clear all shows first
    for show in db_service.get_all_shows():
        db_service.delete_show_and_episodes(show["tmdb_id"])

    show = Show(
        sys_name="TestShow",
        sys_path="/fake/path/TestShow",
        tmdb_name="Test Show",
        tmdb_aliases="alias1, alias2",
        tmdb_id=1,
        tmdb_first_aired=datetime.datetime.now(),
        tmdb_last_aired=datetime.datetime.now(),
        tmdb_year=2020,
        tmdb_overview="Overview",
        tmdb_season_count=1,
        tmdb_episode_count=3,
        tmdb_episode_groups="[]",
        tmdb_episodes_fetched_at=datetime.datetime.now(),
        tmdb_status="Ended",
        tmdb_external_ids="{}",
        fetched_at=datetime.datetime.now()
    )
    db_service.add_show(show)
    result = db_service.get_show_by_name_or_alias("alias2")
    assert result["tmdb_name"] == "Test Show"


# ────────────────────────────────────────────────
# EPISODE MANAGEMENT TESTS
# ────────────────────────────────────────────────

def test_add_episodes_and_query(db_service):
    episode = Episode(
        tmdb_id=1,
        season=1,
        episode=1,
        abs_episode=1,
        episode_type="standard",
        episode_id=101,
        air_date=datetime.datetime.now(),
        fetched_at=datetime.datetime.now(),
        name="Ep 1",
        overview="Ep overview"
    )
    db_service.add_episode(episode)
    assert db_service.episodes_exist(1)

def test_get_episode_by_absolute_number(db_service):
    episode = Episode(
        tmdb_id=1,
        season=1,
        episode=1,
        abs_episode=1,
        episode_type="standard",
        episode_id=101,
        air_date=datetime.datetime.now(),
        fetched_at=datetime.datetime.now(),
        name="Ep 1",
        overview="Ep overview"
    )
    db_service.add_episode(episode)
    result = db_service.get_episode_by_absolute_number(1, 1)
    assert result["abs_episode"] == 1

def test_get_episodes_by_nonexistent_show_name(db_service):
    episodes = db_service.get_episodes_by_show_name("DoesNotExist")
    assert episodes == []

def test_episodes_exist_false(db_service):
    assert not db_service.episodes_exist(9999)


# ────────────────────────────────────────────────
# FILE INVENTORY TESTS
# ────────────────────────────────────────────────

def test_add_inventory_files(db_service):
    now = datetime.datetime.now()
    files = [{
        "name": "file1.txt",
        "size": 100,
        "modified_time": now,
        "path": "/path/to/file1.txt",
        "fetched_at": now,
        "is_dir": False
    }]
    db_service.add_inventory_files(files)
    inventory = db_service.get_inventory_files()
    assert len(inventory) == 1
    assert inventory[0]["name"] == "file1.txt"

def test_add_downloaded_files(db_service):
    now = datetime.datetime.now()
    files = [{
        "name": "downloaded1.txt",
        "size": 200,
        "modified_time": now,
        "path": "/path/to/downloaded1.txt",
        "fetched_at": now,
        "is_dir": False
    }]
    db_service.add_downloaded_files(files)
    downloaded = db_service.get_downloaded_files()
    assert len(downloaded) == 1
    assert downloaded[0]["name"] == "downloaded1.txt"

def test_get_sftp_diffs_returns_expected(db_service):
    now = datetime.datetime.now()
    sftp_files = [{
        "name": "newfile.txt",
        "size": 500,
        "modified_time": now,
        "path": "/remote/path/newfile.txt",
        "fetched_at": now,
        "is_dir": False
    }]
    db_service.clear_sftp_temp_files()
    db_service.insert_sftp_temp_files(sftp_files)
    diffs = db_service.get_sftp_diffs()
    assert len(diffs) == 1
    assert diffs[0]["name"] == "newfile.txt"


# ────────────────────────────────────────────────
# DATABASE BEHAVIOR / EDGE CASE TESTS
# ────────────────────────────────────────────────

def test_delete_show_and_episodes(db_service):
    db_service.delete_show_and_episodes(1)  # Should be safe even if no show exists
    assert not db_service.episodes_exist(1)

def test_delete_nonexistent_show_and_episodes(db_service):
    db_service.delete_show_and_episodes(404)  # Should not raise

def test_sqlite_adapter_registration_error(tmp_path, monkeypatch):
    def mock_register_adapter(*args, **kwargs):
        raise sqlite3.ProgrammingError("Adapter registration failed")

    monkeypatch.setattr(sqlite3, "register_adapter", mock_register_adapter)
    config = {
        "Database": {"type": "sqlite"},
        "SQLite": {"db_file": os.path.join(tmp_path, "test.db")},
        "llm": {"service": "ollama"},
        "ollama": {"model": "ollama3.2"},
    }
    db_service = create_db_service(config)
    # Should not raise anything, just log error

def test_connection_error_handling(tmp_path, monkeypatch):
    def mock_connect(*args, **kwargs):
        raise sqlite3.Error("Connection failed")

    config = {
        "Database": {"type": "sqlite"},
        "SQLite": {"db_file": os.path.join(tmp_path, "test.db")},
        "llm": {"service": "ollama"},
        "ollama": {"model": "ollama3.2"},
    }
    db_service = create_db_service(config)
    monkeypatch.setattr(sqlite3, "connect", mock_connect)

    with pytest.raises(sqlite3.Error):
        with db_service._connection():
            pass
