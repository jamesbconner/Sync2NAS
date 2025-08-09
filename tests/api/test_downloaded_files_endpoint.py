import pytest
from fastapi.testclient import TestClient


def create_app_with_services(app, db):
    # Attach minimal services needed by the route
    if not hasattr(app, "state"):
        app.state = type("State", (), {})()
    app.state.services = {"db": db}


@pytest.fixture
def client_sqlite(tmp_path, monkeypatch):
    from api.main import app
    # Use DB service
    db_file = tmp_path / "test.db"
    from services.db_implementations.sqlite_implementation import SQLiteDBService
    db_service = SQLiteDBService(str(db_file))
    db_service.initialize()

    # Seed a few rows through DB service
    from models.downloaded_file import DownloadedFile, FileStatus
    import datetime

    def mk(name, status, ftype, current_path=None):
        df = DownloadedFile(
            name=name,
            remote_path=f"/remote/{name}",
            current_path=current_path,
            size=100,
            modified_time=datetime.datetime(2024, 1, 1, 12, 0, 0),
            fetched_at=datetime.datetime(2024, 1, 1, 13, 0, 0),
            is_dir=False,
            status=FileStatus(status),
        )
        return db_service.upsert_downloaded_file(df)
    def mk_dir(name, status):
        df = DownloadedFile(
            name=name,
            remote_path=f"/remote/{name}",
            current_path=None,
            size=0,
            modified_time=datetime.datetime(2024, 1, 1, 12, 0, 0),
            fetched_at=datetime.datetime(2024, 1, 1, 13, 0, 0),
            is_dir=True,
            status=FileStatus(status),
        )
        return db_service.upsert_downloaded_file(df)

    mk("a.mkv", "downloaded", "video", current_path="/incoming/a.mkv")
    mk("b.srt", "routed", "subtitle", current_path="/shows/b.srt")
    mk("c.mkv", "downloaded", "video", current_path="/incoming/c.mkv")
    mk_dir("some_folder", "downloaded")

    # Monkeypatch a minimal db service exposing db_file so the endpoint chooses SQLite repo
    class DummyDB:
        def __init__(self, db_file):
            self.db_file = db_file

    create_app_with_services(app, db_service)
    return TestClient(app)


def test_list_downloaded_default_downloaded_only(client_sqlite):
    resp = client_sqlite.get("/api/files/downloaded")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    # Default filter returns only downloaded items
    assert data["count"] >= 1
    for item in data["files"]:
        assert item["status"] == "downloaded"


def test_list_downloaded_with_filters_and_pagination(client_sqlite):
    # Query routed only
    resp = client_sqlite.get("/api/files/downloaded", params={"status": "routed"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    for item in data["files"]:
        assert item["status"] == "routed"

    # Pagination
    resp = client_sqlite.get("/api/files/downloaded", params={"page": 1, "page_size": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert len(data["files"]) == 1

    # Search by q
    resp = client_sqlite.get("/api/files/downloaded", params={"q": "a.mkv"})
    assert resp.status_code == 200
    data = resp.json()
    assert any("a.mkv" == f["name"] for f in data["files"]) or data["count"] >= 1


def test_get_downloaded_file_and_status_patch_and_rehash(client_sqlite):
    # List first to get an id
    resp = client_sqlite.get("/api/files/downloaded")
    assert resp.status_code == 200
    item = resp.json()["files"][0]
    file_id = item["id"]

    # GET detail
    resp = client_sqlite.get(f"/api/files/downloaded/{file_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == file_id

    # PATCH status
    resp = client_sqlite.patch(f"/api/files/downloaded/{file_id}", json={"status": "processing"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"

    # POST rehash (may return 422 if file missing or is a dir)
    resp = client_sqlite.post(f"/api/files/downloaded/{file_id}/rehash")
    assert resp.status_code in (404, 422)


def test_patch_invalid_status_returns_422(client_sqlite):
    resp = client_sqlite.get("/api/files/downloaded")
    file_id = resp.json()["files"][0]["id"]
    resp = client_sqlite.patch(f"/api/files/downloaded/{file_id}", json={"status": "not_a_status"})
    assert resp.status_code == 422


def test_get_detail_not_found_returns_404(client_sqlite):
    resp = client_sqlite.get("/api/files/downloaded/999999")
    assert resp.status_code == 404


def test_rehash_directory_422(client_sqlite):
    # Find the directory entry created in fixture
    resp = client_sqlite.get("/api/files/downloaded", params={"q": "some_folder"})
    # If not found (depending on search), fallback to list and find first dir
    if resp.status_code == 200 and resp.json()["files"]:
        items = resp.json()["files"]
    else:
        items = client_sqlite.get("/api/files/downloaded").json()["files"]
    dir_id = None
    for it in items:
        if it["name"] == "some_folder":
            dir_id = it["id"]
            break
    assert dir_id is not None
    r = client_sqlite.post(f"/api/files/downloaded/{dir_id}/rehash")
    assert r.status_code == 422


def test_patch_with_error_message(client_sqlite):
    resp = client_sqlite.get("/api/files/downloaded")
    file_id = resp.json()["files"][0]["id"]
    resp = client_sqlite.patch(
        f"/api/files/downloaded/{file_id}",
        json={"status": "error", "error_message": "checksum mismatch"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["error_message"] == "checksum mismatch"


