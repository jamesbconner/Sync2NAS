import os
import stat
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from services.sftp_service import SFTPService

@pytest.fixture
def mock_sftp_attr(mocker):
    """Fixture to generate mock SFTP attributes easily."""
    def make_attr(filename, size, mtime, is_dir=False):
        attr = mocker.Mock()
        attr.filename = filename
        attr.st_size = size
        attr.st_mtime = mtime
        attr.st_mode = stat.S_IFDIR if is_dir else stat.S_IFREG
        return attr
    return make_attr

def create_sftp_with_mock_client(mocker):
    """Helper to create an SFTPService with a mocked client and patched reconnect."""
    sftp = SFTPService("host", 22, "user", "keypath")
    sftp.client = mocker.Mock()
    mocker.patch.object(sftp, "reconnect", return_value=None)
    return sftp

# ─────────────────────────────────────────────────────────
# Connection / Context Manager Tests
# ─────────────────────────────────────────────────────────

def test_context_manager_success(mocker):
    mock_key = mocker.Mock()
    mock_transport = mocker.Mock()
    mock_client = mocker.Mock()

    with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_key), \
         patch('paramiko.Transport', return_value=mock_transport), \
         patch('paramiko.SFTPClient.from_transport', return_value=mock_client):
        
        with SFTPService("host", 22, "user", "keypath") as sftp:
            assert sftp.client == mock_client
            mock_transport.connect.assert_called_once_with(username="user", pkey=mock_key)

    mock_transport.close.assert_called_once()
    mock_client.close.assert_called_once()

def test_context_manager_connection_error(mocker):
    mock_transport = mocker.Mock()
    mock_transport.connect.side_effect = Exception("Connection Error")
    mock_key = mocker.Mock()

    with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_key), \
         patch('paramiko.Transport', return_value=mock_transport):
        
        sftp = SFTPService("host", 22, "user", "keypath")
        with pytest.raises(RuntimeError, match="Failed to connect to SFTP server: Connection Error"):
            with sftp:
                pass

# ─────────────────────────────────────────────────────────
# list_remote_dir Tests
# ─────────────────────────────────────────────────────────

def test_list_remote_dir_filters_properly(mocker, mock_sftp_attr):
    sftp = create_sftp_with_mock_client(mocker)
    recent_time = (datetime.now() - timedelta(seconds=30)).timestamp()
    old_time = (datetime.now() - timedelta(minutes=5)).timestamp()

    mock_entries = [
        mock_sftp_attr("valid_video.mkv", 1234, old_time),
        mock_sftp_attr("image.jpg", 2048, old_time),
        mock_sftp_attr("sample_file.mkv", 1024, old_time),
        mock_sftp_attr("new_video.mkv", 1024, recent_time),
        mock_sftp_attr("valid_folder", 0, old_time, is_dir=True),
        mock_sftp_attr("screenshots", 0, old_time, is_dir=True),
    ]

    sftp.client.listdir_attr.return_value = mock_entries
    results = sftp.list_remote_dir("/remote/path")

    names = {entry["name"] for entry in results}
    assert "valid_video.mkv" in names
    assert "valid_folder" in names
    assert "image.jpg" not in names
    assert "sample_file.mkv" not in names
    assert "new_video.mkv" not in names
    assert "screenshots" not in names

def test_list_remote_dir_handles_empty(mocker):
    sftp = create_sftp_with_mock_client(mocker)
    sftp.client.listdir_attr.return_value = []
    assert sftp.list_remote_dir("/remote/path") == []

# ─────────────────────────────────────────────────────────
# list_remote_files Tests
# ─────────────────────────────────────────────────────────

def test_list_remote_files_filters_properly(mocker, mock_sftp_attr):
    sftp = create_sftp_with_mock_client(mocker)
    old_time = (datetime.now() - timedelta(minutes=5)).timestamp()

    mock_entries = [
        mock_sftp_attr("episode1.mkv", 1234, old_time),
        mock_sftp_attr("Thumbs.db", 1234, old_time),
        mock_sftp_attr("regular_folder", 0, old_time, is_dir=True),
        mock_sftp_attr("Sample_folder", 0, old_time, is_dir=True),
    ]

    sftp.client.listdir_attr.return_value = mock_entries
    results = sftp.list_remote_files("/remote/path")

    names = {entry["name"] for entry in results}
    assert "episode1.mkv" in names
    assert "regular_folder" in names
    assert "Thumbs.db" not in names
    assert "Sample_folder" not in names

# ─────────────────────────────────────────────────────────
# list_remote_files_recursive Tests
# ─────────────────────────────────────────────────────────

def test_list_remote_files_recursive_downloads_nested(mocker, mock_sftp_attr):
    sftp = create_sftp_with_mock_client(mocker)
    old_time = (datetime.now() - timedelta(minutes=5)).timestamp()

    dir_attr = mock_sftp_attr("subdir", 0, old_time, is_dir=True)
    file_attr = mock_sftp_attr("episode1.mkv", 1234, old_time)

    sftp.client.listdir_attr.side_effect = [
        [dir_attr],
        [file_attr]
    ]

    results = sftp.list_remote_files_recursive("/remote/path")
    names = {entry["name"] for entry in results}
    assert "episode1.mkv" in names

# ─────────────────────────────────────────────────────────
# download_file / download_dir Tests
# ─────────────────────────────────────────────────────────

def test_download_file_success(mocker, tmp_path):
    sftp = create_sftp_with_mock_client(mocker)
    remote_path = "/remote/file.mkv"
    local_path = tmp_path / "file.mkv"

    sftp.download_file(remote_path, str(local_path))
    sftp.client.get.assert_called_once_with(remote_path, str(local_path))

def test_download_dir_success(mocker, tmp_path, mock_sftp_attr):
    sftp = create_sftp_with_mock_client(mocker)
    remote_root = "/remote"
    local_root = tmp_path / "downloads"

    file_attr = mock_sftp_attr("file1.mkv", 1000, (datetime.now() - timedelta(minutes=5)).timestamp())
    dir_attr = mock_sftp_attr("subdir", 0, (datetime.now() - timedelta(minutes=5)).timestamp(), is_dir=True)
    subfile_attr = mock_sftp_attr("file2.mkv", 500, (datetime.now() - timedelta(minutes=5)).timestamp())

    sftp.client.listdir_attr.side_effect = [
        [file_attr, dir_attr],
        [subfile_attr]
    ]

    mocker.spy(sftp, "download_file")
    mocker.spy(sftp, "download_dir")

    sftp.download_dir(remote_root, str(local_root))

    sftp.download_file.assert_any_call("/remote/file1.mkv", str(local_root / "file1.mkv"))
    sftp.download_file.assert_any_call("/remote/subdir/file2.mkv", str(local_root / "subdir" / "file2.mkv"))
    assert sftp.download_file.call_count == 2
