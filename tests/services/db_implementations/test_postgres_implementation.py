import os
import pytest
import datetime

from services.db_implementations.postgres_implementation import PostgresDBService
from models.downloaded_file import DownloadedFile, FileStatus


PG_CONN = os.getenv(
    "SYNC2NAS_TEST_POSTGRES",
    "host=localhost port=5432 dbname=sync2nas user=postgres password=postgres",
)


@pytest.mark.postgres
def test_pg_initialize_and_upsert_and_search(monkeypatch):
    try:
        db = PostgresDBService(PG_CONN)
        db.initialize()
    except Exception:
        pytest.skip("Postgres not available for tests; set SYNC2NAS_TEST_POSTGRES to enable")

    # Upsert a few records
    now = datetime.datetime(2024, 1, 1, 12, 0, 0)
    files = [
        DownloadedFile(name="a.mkv", remote_path="/remote/a.mkv", size=100, modified_time=now, fetched_at=now, is_dir=False, status=FileStatus.DOWNLOADED),
        DownloadedFile(name="b.srt", remote_path="/remote/b.srt", size=10, modified_time=now, fetched_at=now, is_dir=False, status=FileStatus.ROUTED, current_path="/shows/b.srt"),
        DownloadedFile(name="c.mkv", remote_path="/remote/c.mkv", size=200, modified_time=now, fetched_at=now, is_dir=False, status=FileStatus.DOWNLOADED),
    ]
    for f in files:
        db.upsert_downloaded_file(f)

    # Get by remote_path
    got = db.get_downloaded_file_by_remote_path("/remote/a.mkv")
    assert got is not None
    assert got.name == "a.mkv"

    # Search downloaded only
    items, total = db.search_downloaded_files(status=FileStatus.DOWNLOADED, page=1, page_size=10)
    assert total >= 2
    assert all(it.status == FileStatus.DOWNLOADED for it in items)

    # Update location by id and mark error
    if got and got.id:
        db.update_downloaded_file_location(got.id, new_path="/incoming/a.mkv", new_status=FileStatus.ROUTED)
        db.mark_downloaded_file_error(got.id, "error message")
        got2 = db.get_downloaded_file_by_id(got.id)
        assert got2 is not None
        assert got2.status in (FileStatus.ROUTED, FileStatus.ERROR)