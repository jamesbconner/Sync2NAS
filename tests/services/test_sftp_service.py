import os
import stat
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from services.sftp_service import SFTPService


@pytest.fixture
def mock_sftp_attr(mocker):
    def make_attr(filename, st_size, st_mtime, is_dir=False):
        mock_attr = mocker.Mock()
        mock_attr.filename = filename
        mock_attr.st_size = st_size
        mock_attr.st_mtime = st_mtime
        mock_attr.st_mode = stat.S_IFDIR if is_dir else stat.S_IFREG
        return mock_attr
    return make_attr


def test_context_manager_initializes_and_cleans_up(mocker):
    mock_key = mocker.Mock()
    mock_transport = mocker.Mock()
    mock_client = mocker.Mock()

    with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_key), \
         patch('paramiko.Transport', return_value=mock_transport), \
         patch('paramiko.SFTPClient.from_transport', return_value=mock_client):
        
        sftp = SFTPService("host", 22, "user", "keypath")
        with sftp as s:
            assert s.client == mock_client
            mock_transport.connect.assert_called_once_with(username="user", pkey=mock_key)
            mock_transport.close.assert_not_called()
            mock_client.close.assert_not_called() # Covered in the __exit__ method
        
        # After context manager exits, both transport and client should be closed
        mock_transport.close.assert_called_once()
        mock_client.close.assert_called_once()

        # Verify the transport was properly closed
        assert mock_transport.close.call_count == 1
        assert mock_client.close.call_count == 1


def test_list_remote_dir_filters_properly(mocker, mock_sftp_attr):
    recent = (datetime.now() - timedelta(seconds=30)).timestamp()
    old = (datetime.now() - timedelta(minutes=5)).timestamp()

    mock_entries = [
        mock_sftp_attr("valid_video.mkv", 1024, old),
        mock_sftp_attr("image.jpg", 2048, old),
        mock_sftp_attr("sample_movie.mkv", 1024, old),
        mock_sftp_attr("new_video.mkv", 1024, recent),
        mock_sftp_attr("valid_folder", 0, old, is_dir=True),
        mock_sftp_attr("screenshots", 0, old, is_dir=True),
    ]

    mock_client = mocker.Mock()
    mock_client.listdir_attr.return_value = mock_entries

    sftp_service = SFTPService("host", 22, "user", "keypath")
    sftp_service.client = mock_client

    result = sftp_service.list_remote_dir("/remote/path")

    assert len(result) == 2
    names = {entry["name"] for entry in result}
    assert "valid_video.mkv" in names
    assert "valid_folder" in names
    assert "image.jpg" not in names
    assert "sample_movie.mkv" not in names
    assert "new_video.mkv" not in names
    assert "screenshots" not in names


def test_list_remote_dir_handles_empty_directory(mocker):
    mock_client = mocker.Mock()
    mock_client.listdir_attr.return_value = []

    sftp_service = SFTPService("host", 22, "user", "keypath")
    sftp_service.client = mock_client

    result = sftp_service.list_remote_dir("/remote/path")
    assert result == []


def test_list_remote_dir_handles_errors(mocker):
    mock_client = mocker.Mock()
    mock_client.listdir_attr.side_effect = Exception("SFTP Error")

    sftp_service = SFTPService("host", 22, "user", "keypath")
    sftp_service.client = mock_client

    with pytest.raises(Exception) as exc_info:
        sftp_service.list_remote_dir("/remote/path")
    assert str(exc_info.value) == "SFTP Error"


def test_list_remote_files_filters_properly(mocker, mock_sftp_attr):
    recent = (datetime.now() - timedelta(seconds=30)).timestamp()
    old = (datetime.now() - timedelta(minutes=5)).timestamp()

    mock_entries = [
        mock_sftp_attr("valid_video.mkv", 1024, old),
        mock_sftp_attr("image.jpg", 2048, old),
        mock_sftp_attr("sample_movie.mkv", 1024, old),
        mock_sftp_attr("new_video.mkv", 1024, recent),
        mock_sftp_attr("valid_folder", 0, old, is_dir=True),
        mock_sftp_attr("screenshots", 0, old, is_dir=True),
    ]

    mock_client = mocker.Mock()
    mock_client.listdir_attr.return_value = mock_entries

    sftp_service = SFTPService("host", 22, "user", "keypath")
    sftp_service.client = mock_client

    result = sftp_service.list_remote_files("/remote/path")

    assert len(result) == 2
    names = {entry["name"] for entry in result}
    assert "valid_video.mkv" in names
    assert "valid_folder" in names
    assert "image.jpg" not in names
    assert "sample_movie.mkv" not in names
    assert "new_video.mkv" not in names
    assert "screenshots" not in names


def test_download_file_creates_directory_and_downloads_file(mocker, tmp_path):
    mock_client = mocker.Mock()
    sftp = SFTPService("host", 22, "user", "key")
    sftp.client = mock_client

    remote_path = "/remote/path/file.txt"
    local_path = tmp_path / "downloads" / "file.txt"

    makedirs_spy = mocker.spy(os, "makedirs")
    get_mock = mock_client.get

    sftp.download_file(remote_path, str(local_path))

    makedirs_spy.assert_called_once_with(str(local_path.parent), exist_ok=True)
    get_mock.assert_called_once_with(remote_path, str(local_path))


def test_download_file_handles_errors(mocker, tmp_path):
    mock_client = mocker.Mock()
    mock_client.get.side_effect = Exception("Download Error")
    sftp = SFTPService("host", 22, "user", "key")
    sftp.client = mock_client

    remote_path = "/remote/path/file.txt"
    local_path = tmp_path / "downloads" / "file.txt"

    with pytest.raises(Exception) as exc_info:
        sftp.download_file(remote_path, str(local_path))
    assert str(exc_info.value) == "Download Error"


def test_download_dir_recursively_downloads_nested_structure(mocker, tmp_path):
    sftp = SFTPService("host", 22, "user", "key")
    mock_client = mocker.Mock()
    sftp.client = mock_client

    def make_attr(name, is_dir):
        attr = mocker.Mock()
        attr.filename = name
        attr.st_mode = 0o040755 if is_dir else 0o100644
        return attr

    mock_client.listdir_attr.side_effect = [
        [make_attr("file1.txt", False), make_attr("subdir", True)],
        [make_attr("file2.txt", False)]
    ]

    mocker.spy(sftp, "download_file")

    remote_root = "/remote/path"
    local_root = tmp_path / "downloads"

    sftp.download_dir(remote_root, str(local_root))

    sftp.download_file.assert_has_calls([
        mocker.call(f"{remote_root}/file1.txt", str(local_root / "file1.txt")),
        mocker.call(f"{remote_root}/subdir/file2.txt", str(local_root / "subdir" / "file2.txt")),
    ])
    assert sftp.download_file.call_count == 2


def test_download_dir_handles_errors(mocker, tmp_path):
    sftp = SFTPService("host", 22, "user", "key")
    mock_client = mocker.Mock()
    sftp.client = mock_client

    def make_attr(name, is_dir):
        attr = mocker.Mock()
        attr.filename = name
        attr.st_mode = 0o040755 if is_dir else 0o100644
        return attr

    mock_client.listdir_attr.side_effect = Exception("List Directory Error")

    remote_root = "/remote/path"
    local_root = tmp_path / "downloads"

    with pytest.raises(Exception) as exc_info:
        sftp.download_dir(remote_root, str(local_root))
    assert str(exc_info.value) == "List Directory Error"


def test_context_manager_handles_connection_error(mocker):
    mock_key = mocker.Mock()
    mock_transport = mocker.Mock()
    mock_client = mocker.Mock()

    # Simulate an error during connection
    mock_transport.connect.side_effect = Exception("Connection Error")

    with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_key), \
         patch('paramiko.Transport', return_value=mock_transport), \
         patch('paramiko.SFTPClient.from_transport', return_value=mock_client):
        
        sftp = SFTPService("host", 22, "user", "keypath")
        with pytest.raises(Exception) as exc_info:
            with sftp as s:
                pass
        assert str(exc_info.value) == "Connection Error"
        
        # Verify cleanup was called
        mock_transport.close.assert_called_once()


def test_context_manager_handles_client_close_error(mocker):
    mock_key = mocker.Mock()
    mock_transport = mocker.Mock()
    mock_client = mocker.Mock()

    # Simulate an error during client close
    mock_client.close.side_effect = Exception("Client Close Error")

    with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_key), \
         patch('paramiko.Transport', return_value=mock_transport), \
         patch('paramiko.SFTPClient.from_transport', return_value=mock_client):
        
        sftp = SFTPService("host", 22, "user", "keypath")
        with sftp as s:
            pass
        
        # Verify transport was still closed despite client close error
        mock_transport.close.assert_called_once()


def test_context_manager_handles_transport_close_error(mocker):
    mock_key = mocker.Mock()
    mock_transport = mocker.Mock()
    mock_client = mocker.Mock()

    # Simulate an error during transport close
    mock_transport.close.side_effect = Exception("Transport Close Error")

    with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_key), \
         patch('paramiko.Transport', return_value=mock_transport), \
         patch('paramiko.SFTPClient.from_transport', return_value=mock_client):
        
        sftp = SFTPService("host", 22, "user", "keypath")
        with sftp as s:
            pass
        
        # Verify client was still closed despite transport close error
        mock_client.close.assert_called_once()
