import sqlite3
import pytest
import datetime
from services.db_service import DBService


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"

@pytest.fixture
def db_service(db_path):
    db = DBService(str(db_path))
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

def test_reset_sftp_temp_files_creates_clean_table(db_service):
    # Preload garbage data
    with db_service._connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS sftp_temp_files (name TEXT)")
        conn.execute("INSERT INTO sftp_temp_files (name) VALUES ('junk')")
        conn.commit()

    db_service.reset_sftp_temp_files()

    # Should now match the expected schema
    with db_service._connection() as conn:
        cursor = conn.execute("PRAGMA table_info(sftp_temp_files)")
        columns = [row[1] for row in cursor.fetchall()]

    assert set(columns) >= {
        "name", "path", "size", "modified_time", "fetched_at", "is_dir"
    }

def test_insert_sftp_temp_files_adds_records(db_service, sftp_entries):
    db_service.reset_sftp_temp_files()
    db_service.insert_sftp_temp_files(sftp_entries)

    with db_service._connection() as conn:
        cursor = conn.execute("SELECT * FROM sftp_temp_files")
        results = cursor.fetchall()

    assert len(results) == len(sftp_entries)
    for row, entry in zip(results, sftp_entries):
        assert row[0] == entry["name"]
        assert row[1] == entry["path"]
        assert row[2] == entry["size"]
        assert isinstance(row[3], str)  # ISO timestamp
        assert isinstance(row[4], str)
        assert row[5] == int(entry["is_dir"])

def test_add_downloaded_file_inserts_single(db_service):
    file = {
        "name": "example.txt",
        "size": 1234,
        "modified_time": datetime.datetime(2024, 1, 1, 12, 0),
        "path": "/remote/path/example.txt",
        "is_dir": False,
        "fetched_at": datetime.datetime.now(),
    }

    db_service.reset_sftp_temp_files()  # ensures table exists
    db_service.add_downloaded_file(file)

    with db_service._connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM downloaded_files").fetchone()
        assert row["name"] == "example.txt"
        assert row["path"] == "/remote/path/example.txt"

def test_add_downloaded_files_inserts_multiple(db_service):
    now = datetime.datetime.now()
    files = [
        {
            "name": f"file{i}.mp4",
            "size": 1000 + i,
            "modified_time": now,
            "path": f"/remote/path/file{i}.mp4",
            "is_dir": False,
            "fetched_at": now,
        }
        for i in range(3)
    ]

    db_service.reset_sftp_temp_files()
    db_service.add_downloaded_files(files)

    with db_service._connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM downloaded_files").fetchall()
        assert len(rows) == 3
        names = [row["name"] for row in rows]
        assert "file0.mp4" in names
        assert "file1.mp4" in names
        assert "file2.mp4" in names

def test_get_sftp_diffs_returns_expected_new_files(db_service):
    now = datetime.datetime.now()

    # Files in sftp_temp_files
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

    # Only this file was downloaded earlier
    downloaded_file = {
        "name": "existing_file.mkv",
        "size": 3000,
        "modified_time": now,
        "path": "/remote/path/existing_file.mkv",
        "is_dir": False,
        "fetched_at": now,
    }

    db_service.reset_sftp_temp_files()
    db_service.insert_sftp_temp_files(temp_files)
    db_service.add_downloaded_file(downloaded_file)

    diffs = db_service.get_sftp_diffs()

    # Should only return the two "new" files
    diff_names = {entry["name"] for entry in diffs}
    assert len(diffs) == 2
    assert "new_file1.mkv" in diff_names
    assert "new_file2.mkv" in diff_names
    assert "existing_file.mkv" not in diff_names