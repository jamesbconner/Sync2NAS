import sqlite3
import pytest
import datetime
from services.db_factory import create_db_service

# ────────────────────────────────────────────────
# FIXTURES
# ────────────────────────────────────────────────

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"

@pytest.fixture
def db_service(db_path):
    config = {
        "Database": {"type": "sqlite"},
        "SQLite": {"db_file": str(db_path)},
        "llm": {"service": "ollama"},
        "ollama": {"model": "gemma3:12b"},
    }
    db = create_db_service(config)
    db.initialize()
    return db

@pytest.fixture
def sftp_entries():
    now = datetime.datetime.now()
    return [
        {
            "name": "file1.txt",
            "path": "/remote/path/file1.txt",
            "size": 1234,
            "modified_time": now - datetime.timedelta(days=1),
            "fetched_at": now,
            "is_dir": False,
        },
        {
            "name": "some_folder",
            "path": "/remote/path/some_folder",
            "size": 0,
            "modified_time": now - datetime.timedelta(days=2),
            "fetched_at": now,
            "is_dir": True,
        },
    ]

# ────────────────────────────────────────────────
# TESTS
# ────────────────────────────────────────────────

def test_clear_sftp_temp_files_removes_all_records(db_service):
    """Ensure clearing the temp files table leaves it empty."""
    # Insert dummy entry
    db_service.insert_sftp_temp_files([{
        "name": "junkfile",
        "path": "/remote/path/junkfile",
        "size": 1,
        "modified_time": datetime.datetime.now(),
        "fetched_at": datetime.datetime.now(),
        "is_dir": False,
    }])

    db_service.clear_sftp_temp_files()

    with db_service._connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM sftp_temp_files")
        assert cursor.fetchone()[0] == 0

def test_insert_sftp_temp_files_persists_entries(db_service, sftp_entries):
    """Inserted temp entries should match what was provided."""
    db_service.clear_sftp_temp_files()
    db_service.insert_sftp_temp_files(sftp_entries)

    with db_service._connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM sftp_temp_files").fetchall()

    assert len(rows) == len(sftp_entries)

    for row, expected in zip(rows, sftp_entries):
        for key in expected:
            assert row[key] == expected[key]

def test_add_downloaded_file_inserts_one_record(db_service):
    """Adding a single downloaded file should store it correctly."""
    now = datetime.datetime.now()
    file = {
        "name": "example.txt",
        "size": 1234,
        "modified_time": now,
        "path": "/remote/path/example.txt",
        "is_dir": False,
        "fetched_at": now,
    }

    db_service.clear_sftp_temp_files()
    db_service.add_downloaded_file(file)

    with db_service._connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM downloaded_files").fetchone()

    assert row is not None
    for key in file:
        assert row[key] == file[key]

def test_add_downloaded_files_inserts_multiple_records(db_service):
    """Adding multiple files should insert each one properly."""
    now = datetime.datetime.now()
    files = [
        {
            "name": f"file_{i}.mkv",
            "size": 1000 + i,
            "modified_time": now,
            "path": f"/remote/path/file_{i}.mkv",
            "is_dir": False,
            "fetched_at": now,
        }
        for i in range(3)
    ]

    db_service.clear_sftp_temp_files()
    db_service.add_downloaded_files(files)

    with db_service._connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM downloaded_files").fetchall()

    assert len(rows) == 3
    inserted_names = {row["name"] for row in rows}
    expected_names = {file["name"] for file in files}
    assert inserted_names == expected_names

def test_get_sftp_diffs_returns_only_new_files(db_service):
    """Diffs should return files not already downloaded."""
    now = datetime.datetime.now()

    temp_files = [
        {
            "name": "new_file1.mkv",
            "size": 1000,
            "modified_time": now,
            "path": "/remote/path/new_file1.mkv",
            "is_dir": False,
            "fetched_at": now,
        },
        {
            "name": "new_file2.mkv",
            "size": 2000,
            "modified_time": now,
            "path": "/remote/path/new_file2.mkv",
            "is_dir": False,
            "fetched_at": now,
        },
        {
            "name": "existing_file.mkv",
            "size": 3000,
            "modified_time": now,
            "path": "/remote/path/existing_file.mkv",
            "is_dir": False,
            "fetched_at": now,
        },
    ]

    downloaded_file = {
        "name": "existing_file.mkv",
        "size": 3000,
        "modified_time": now,
        "path": "/remote/path/existing_file.mkv",
        "is_dir": False,
        "fetched_at": now,
    }

    db_service.clear_sftp_temp_files()
    db_service.insert_sftp_temp_files(temp_files)
    db_service.add_downloaded_file(downloaded_file)

    diffs = db_service.get_sftp_diffs()

    diff_names = {entry["name"] for entry in diffs}
    assert "new_file1.mkv" in diff_names
    assert "new_file2.mkv" in diff_names
    assert "existing_file.mkv" not in diff_names
