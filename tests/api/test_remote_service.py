import pytest
from unittest.mock import MagicMock
from api.services.remote_service import RemoteService

# Helper for running async methods in pytest
import asyncio
def asyncio_run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def test_download_from_remote_success(mock_sftp_service, db_service, config, mocker):
    """Test that download_from_remote returns success when files are downloaded successfully."""
    mocker.patch("api.services.remote_service.parse_sftp_paths", return_value=["/remote/path"])
    mocker.patch("api.services.remote_service.downloader", return_value=None)
    mock_sftp_service.__enter__.return_value = mock_sftp_service
    mock_sftp_service.__exit__.return_value = None
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    result = asyncio_run(remote_service.download_from_remote(dry_run=False))
    assert result["success"] is True
    assert result["files_downloaded"] == 0
    assert "completed" in result["message"]


def test_download_from_remote_no_paths(mock_sftp_service, db_service, config, mocker):
    """Test that download_from_remote raises ValueError if no SFTP paths are defined in config."""
    mocker.patch("api.services.remote_service.parse_sftp_paths", return_value=[])
    mock_sftp_service.__enter__.return_value = mock_sftp_service
    mock_sftp_service.__exit__.return_value = None
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    with pytest.raises(ValueError):
        asyncio_run(remote_service.download_from_remote(dry_run=False))


def test_download_from_remote_exception(mock_sftp_service, db_service, config, mocker):
    """Test that download_from_remote raises Exception if the download orchestrator fails."""
    mocker.patch("api.services.remote_service.parse_sftp_paths", return_value=["/remote/path"])
    mocker.patch("api.services.remote_service.downloader", side_effect=Exception("fail!"))
    mock_sftp_service.__enter__.return_value = mock_sftp_service
    mock_sftp_service.__exit__.return_value = None
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    with pytest.raises(Exception) as exc:
        asyncio_run(remote_service.download_from_remote(dry_run=False))
    assert "fail!" in str(exc.value)


def test_list_remote_files_success(mock_sftp_service, db_service, config, mocker):
    """Test that list_remote_files returns a list of files from the remote SFTP server."""
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    result = asyncio_run(remote_service.list_remote_files())
    assert result["success"] is True
    assert isinstance(result["files"], list)
    assert result["count"] == len(result["files"])


def test_list_remote_files_recursive(mock_sftp_service, db_service, config, mocker):
    """Test that list_remote_files returns files recursively when recursive=True."""
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    result = asyncio_run(remote_service.list_remote_files(recursive=True))
    assert result["success"] is True
    assert isinstance(result["files"], list)
    assert result["count"] == len(result["files"])


def test_list_remote_files_populate_temp(mock_sftp_service, db_service, config, mocker):
    """Test that list_remote_files populates the SFTP temp table when populate_sftp_temp=True."""
    mock_insert = mocker.patch.object(db_service, "insert_sftp_temp_files", return_value=None)
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    result = asyncio_run(remote_service.list_remote_files(populate_sftp_temp=True))
    mock_insert.assert_called_once()
    assert result["success"] is True


def test_list_remote_files_exception(mock_sftp_service, db_service, config, mocker):
    """Test that list_remote_files raises Exception if the SFTP service fails."""
    mock_sftp_service.list_remote_dir.side_effect = Exception("faildir")
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    with pytest.raises(Exception) as exc:
        asyncio_run(remote_service.list_remote_files())
    assert "faildir" in str(exc.value)


def test_get_connection_status_connected(mock_sftp_service, db_service, config):
    """Test that get_connection_status returns connected status when SFTP connection is successful."""
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    result = asyncio_run(remote_service.get_connection_status())
    assert result["success"] is True
    assert result["status"] == "connected"
    assert result["host"] == config["sftp"]["host"]


def test_get_connection_status_disconnected(mock_sftp_service, db_service, config, mocker):
    """Test that get_connection_status returns disconnected status and error message when SFTP connection fails."""
    mock_sftp_service.list_remote_dir.side_effect = Exception("failconn")
    remote_service = RemoteService(mock_sftp_service, db_service, config)
    result = asyncio_run(remote_service.get_connection_status())
    assert result["success"] is False
    assert result["status"] == "disconnected"
    assert "failconn" in result["error"] 