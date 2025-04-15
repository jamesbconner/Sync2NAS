import pytest
from utils.sftp_orchestrator import process_sftp_diffs

@pytest.fixture
def mock_sftp_service(mocker):
    return mocker.Mock()

@pytest.fixture
def mock_db_service(mocker):
    return mocker.Mock()

def test_process_sftp_diffs_downloads_files(tmp_path, mock_sftp_service, mock_db_service):
    remote_base = "/remote"
    local_base = tmp_path
    now = "2024-01-01T12:00:00"

    diffs = [
        {
            "name": "file1.mkv",
            "path": "/remote/file1.mkv",
            "size": 100,
            "modified_time": now,
            "fetched_at": now,
            "is_dir": False,
        },
        {
            "name": "folder1",
            "path": "/remote/folder1",
            "size": 0,
            "modified_time": now,
            "fetched_at": now,
            "is_dir": True,
        },
    ]

    process_sftp_diffs(
        sftp_service=mock_sftp_service,
        db_service=mock_db_service,
        diffs=diffs,
        remote_base=remote_base,
        local_base=str(local_base),
        dry_run=False,
    )

    mock_sftp_service.download_file.assert_called_once_with(
        "/remote/file1.mkv", str(local_base / "file1.mkv")
    )
    mock_sftp_service.download_dir.assert_called_once_with(
        "/remote/folder1", str(local_base / "folder1")
    )
    assert mock_db_service.add_downloaded_file.call_count == 2

def test_process_sftp_diffs_dry_run(tmp_path, mock_sftp_service, mock_db_service):
    now = "2024-01-01T12:00:00"

    diffs = [
        {
            "name": "file1.mkv",
            "path": "/remote/file1.mkv",
            "size": 100,
            "modified_time": now,
            "fetched_at": now,
            "is_dir": False,
        }
    ]

    process_sftp_diffs(
        sftp_service=mock_sftp_service,
        db_service=mock_db_service,
        diffs=diffs,
        remote_base="/remote",
        local_base=str(tmp_path),
        dry_run=True,
    )

    mock_sftp_service.download_file.assert_not_called()
    mock_sftp_service.download_dir.assert_not_called()
    mock_db_service.add_downloaded_file.assert_not_called()
