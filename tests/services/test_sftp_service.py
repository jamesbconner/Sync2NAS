import os
import stat
import pytest
import paramiko
import socket
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from services.sftp_service import SFTPService, retry_sftp_operation

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
# Retry Decorator Tests
# ─────────────────────────────────────────────────────────

def test_retry_decorator_success(mocker):
    """Test that retry decorator works correctly on successful operations."""
    mock_func = mocker.Mock(return_value="success")
    mock_func.__name__ = "test_operation"
    
    decorated_func = retry_sftp_operation(mock_func)
    
    # Mock the sleep function to avoid actual delays
    mocker.patch('time.sleep')
    
    result = decorated_func(None, "arg1", "arg2")
    
    assert result == "success"
    mock_func.assert_called_once_with(None, "arg1", "arg2")

def test_retry_decorator_retries_on_ssh_exception(mocker):
    """Test that retry decorator retries on SSHException and eventually succeeds."""
    mock_func = mocker.Mock()
    mock_func.__name__ = "test_operation"
    mock_func.side_effect = [paramiko.SSHException("Connection lost"), "success"]
    
    decorated_func = retry_sftp_operation(mock_func)
    
    # Mock the sleep function to avoid actual delays
    mocker.patch('time.sleep')
    
    # Mock the reconnect method
    mock_self = mocker.Mock()
    mock_self.reconnect = mocker.Mock()
    
    result = decorated_func(mock_self, "arg1")
    
    assert result == "success"
    assert mock_func.call_count == 2
    mock_self.reconnect.assert_called_once()

def test_retry_decorator_retries_on_socket_error(mocker):
    """Test that retry decorator retries on socket.error and eventually succeeds."""
    mock_func = mocker.Mock()
    mock_func.__name__ = "test_operation"
    mock_func.side_effect = [socket.error("Network error"), "success"]
    
    decorated_func = retry_sftp_operation(mock_func)
    
    # Mock the sleep function to avoid actual delays
    mocker.patch('time.sleep')
    
    # Mock the reconnect method
    mock_self = mocker.Mock()
    mock_self.reconnect = mocker.Mock()
    
    result = decorated_func(mock_self, "arg1")
    
    assert result == "success"
    assert mock_func.call_count == 2
    mock_self.reconnect.assert_called_once()

def test_retry_decorator_fails_after_max_retries(mocker):
    """Test that retry decorator raises exception after max retries."""
    mock_func = mocker.Mock()
    mock_func.__name__ = "test_operation"
    mock_func.side_effect = paramiko.SSHException("Connection lost")
    
    decorated_func = retry_sftp_operation(mock_func)
    
    # Mock the sleep function to avoid actual delays
    mocker.patch('time.sleep')
    
    # Mock the reconnect method
    mock_self = mocker.Mock()
    mock_self.reconnect = mocker.Mock()
    
    with pytest.raises(paramiko.SSHException, match="Connection lost"):
        decorated_func(mock_self, "arg1")
    
    assert mock_func.call_count == 3  # Initial + 2 retries
    assert mock_self.reconnect.call_count == 2

def test_retry_decorator_with_other_exception(mocker):
    """Test that retry decorator doesn't retry on non-SSH/socket exceptions."""
    mock_func = mocker.Mock()
    mock_func.__name__ = "test_operation"
    mock_func.side_effect = ValueError("Some other error")
    
    decorated_func = retry_sftp_operation(mock_func)
    
    # Mock the sleep function to avoid actual delays
    mocker.patch('time.sleep')
    
    # Mock the reconnect method
    mock_self = mocker.Mock()
    mock_self.reconnect = mocker.Mock()
    
    with pytest.raises(ValueError, match="Some other error"):
        decorated_func(mock_self, "arg1")
    
    assert mock_func.call_count == 1  # No retries for non-SSH/socket errors
    mock_self.reconnect.assert_not_called()

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

def test_context_manager_exit_with_client_close_error(mocker):
    """Test context manager exit when client.close() raises an exception."""
    sftp = SFTPService("host", 22, "user", "keypath")
    mock_client = mocker.Mock()
    mock_transport = mocker.Mock()
    sftp.client = mock_client
    sftp.transport = mock_transport
    mock_client.close.side_effect = Exception("Client close error")
    
    # Should not raise exception, should log it
    sftp.__exit__(None, None, None)
    
    mock_client.close.assert_called_once()
    # transport.close should still be called even if client.close fails
    mock_transport.close.assert_called_once()

def test_context_manager_exit_with_transport_close_error(mocker):
    """Test context manager exit when transport.close() raises an exception."""
    sftp = SFTPService("host", 22, "user", "keypath")
    mock_client = mocker.Mock()
    mock_transport = mocker.Mock()
    sftp.client = mock_client
    sftp.transport = mock_transport
    mock_transport.close.side_effect = Exception("Transport close error")
    
    # Should not raise exception, should log it
    sftp.__exit__(None, None, None)
    
    # client.close should be called first
    mock_client.close.assert_called_once()
    mock_transport.close.assert_called_once()

def test_context_manager_exit_with_none_client_and_transport(mocker):
    """Test context manager exit when client and transport are None."""
    sftp = SFTPService("host", 22, "user", "keypath")
    sftp.client = None
    sftp.transport = None
    
    # Should not raise exception
    sftp.__exit__(None, None, None)

# ─────────────────────────────────────────────────────────
# Connection Method Tests
# ─────────────────────────────────────────────────────────

def test_connect_success(mocker):
    mock_key = mocker.Mock()
    mock_transport = mocker.Mock()
    mock_client = mocker.Mock()
    
    with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_key), \
         patch('paramiko.Transport', return_value=mock_transport), \
         patch('paramiko.SFTPClient.from_transport', return_value=mock_client):
        
        sftp = SFTPService("host", 22, "user", "keypath")
        result = sftp.connect()
        
        assert result == sftp
        assert sftp.client == mock_client
        assert sftp.transport == mock_transport
        mock_transport.connect.assert_called_once_with(username="user", pkey=mock_key)

def test_connect_failure(mocker):
    mock_key = mocker.Mock()
    mock_transport = mocker.Mock()
    mock_transport.connect.side_effect = Exception("Connection failed")
    
    with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_key), \
         patch('paramiko.Transport', return_value=mock_transport):
        
        sftp = SFTPService("host", 22, "user", "keypath")
        
        with pytest.raises(RuntimeError, match="Failed to connect to SFTP server: Connection failed"):
            sftp.connect()

def test_disconnect_success(mocker):
    sftp = SFTPService("host", 22, "user", "keypath")
    mock_client = mocker.Mock()
    mock_transport = mocker.Mock()
    sftp.client = mock_client
    sftp.transport = mock_transport
    
    sftp.disconnect()
    
    mock_client.close.assert_called_once()
    mock_transport.close.assert_called_once()
    assert sftp.client is None
    assert sftp.transport is None

def test_disconnect_with_exception(mocker):
    sftp = SFTPService("host", 22, "user", "keypath")
    mock_client = mocker.Mock()
    mock_transport = mocker.Mock()
    sftp.client = mock_client
    sftp.transport = mock_transport
    mock_client.close.side_effect = Exception("Close error")
    
    # Should not raise exception, should log it
    sftp.disconnect()
    
    mock_client.close.assert_called_once()
    # When client.close() raises an exception, transport.close() is not called
    # because the exception is caught by the try-except block
    mock_transport.close.assert_not_called()

def test_disconnect_with_none_client_and_transport(mocker):
    sftp = SFTPService("host", 22, "user", "keypath")
    sftp.client = None
    sftp.transport = None
    
    # Should not raise exception
    sftp.disconnect()

def test_reconnect_success(mocker):
    sftp = SFTPService("host", 22, "user", "keypath")
    mocker.patch.object(sftp, 'disconnect')
    mocker.patch.object(sftp, 'connect', return_value=sftp)
    
    result = sftp.reconnect()
    
    sftp.disconnect.assert_called_once()
    sftp.connect.assert_called_once()
    assert result == sftp

def test_reconnect_failure(mocker):
    sftp = SFTPService("host", 22, "user", "keypath")
    mocker.patch.object(sftp, 'disconnect')
    mocker.patch.object(sftp, 'connect', side_effect=Exception("Reconnect failed"))
    
    with pytest.raises(RuntimeError, match="Failed to reconnect to SFTP server: Reconnect failed"):
        sftp.reconnect()
    
    sftp.disconnect.assert_called_once()
    sftp.connect.assert_called_once()

# ─────────────────────────────────────────────────────────
# Truncation Method Tests
# ─────────────────────────────────────────────────────────

def test_truncate_filename_with_llm_service(mocker):
    """Test filename truncation using LLM service."""
    sftp = SFTPService("host", 22, "user", "keypath")
    mock_llm = mocker.Mock()
    mock_llm.suggest_short_filename.return_value = "short_name.mkv"
    sftp.llm_service = mock_llm
    
    # Mock os.path.abspath to return a reasonable length
    mocker.patch('os.path.abspath', return_value="/short/path")
    
    result = sftp._truncate_filename("very_long_filename_that_needs_truncation.mkv", 
                                   mock_llm, 100, "/base", "dir")
    
    assert result == "short_name.mkv"
    mock_llm.suggest_short_filename.assert_called_once()

def test_truncate_filename_with_llm_service_path_too_long(mocker):
    """Test filename truncation when LLM suggestion is still too long."""
    sftp = SFTPService("host", 22, "user", "keypath")
    mock_llm = mocker.Mock()
    mock_llm.suggest_short_filename.return_value = "still_too_long_name.mkv"
    sftp.llm_service = mock_llm
    
    # Mock os.path.abspath to return a path that makes the total too long
    def mock_abspath(path):
        if "still_too_long_name.mkv" in path:
            return "x" * 300  # Too long
        return "/short/path"
    
    mocker.patch('os.path.abspath', side_effect=mock_abspath)
    
    # Mock parse_filename to return structured data
    mock_parser_result = {
        'show_name': 'Test Show',
        'season': '01',
        'episode': '01'
    }
    mocker.patch('services.sftp_service.parse_filename', return_value=mock_parser_result)
    
    result = sftp._truncate_filename("very_long_filename_that_needs_truncation.mkv", 
                                   mock_llm, 100, "/base", "dir")
    
    # Should fall back to regex parsing
    assert "Test Show.S01E01.mkv" in result

def test_truncate_filename_without_llm_service(mocker):
    """Test filename truncation without LLM service."""
    sftp = SFTPService("host", 22, "user", "keypath")
    sftp.llm_service = None
    
    # Mock parse_filename to return structured data
    mock_parser_result = {
        'show_name': 'Test Show',
        'season': '01',
        'episode': '01'
    }
    mocker.patch('services.sftp_service.parse_filename', return_value=mock_parser_result)
    
    result = sftp._truncate_filename("test_show_s01e01.mkv", None, 100, "/base", "dir")
    
    assert "Test Show.S01E01.mkv" in result

def test_truncate_filename_fallback_truncation(mocker):
    """Test filename truncation fallback when parsing fails."""
    sftp = SFTPService("host", 22, "user", "keypath")
    sftp.llm_service = None
    
    # Mock parse_filename to return empty result
    mocker.patch('services.sftp_service.parse_filename', return_value={})
    
    # Mock os.path.abspath to return a path that makes the total too long
    def mock_abspath(path):
        if "very_long_filename_that_needs_truncation.mkv" in path:
            return "x" * 100  # Long path
        return "/short/path"
    
    mocker.patch('os.path.abspath', side_effect=mock_abspath)
    
    result = sftp._truncate_filename("very_long_filename_that_needs_truncation.mkv", None, 50, "/base", "dir")
    
    # Should truncate the original filename
    assert len(result) < len("very_long_filename_that_needs_truncation.mkv")

def test_truncate_for_windows_path_no_truncation_needed(mocker):
    """Test path truncation when no truncation is needed."""
    sftp = create_sftp_with_mock_client(mocker)
    
    # Mock _list_remote_files_recursive_helper to return short filenames
    mock_entries = [
        {'name': 'short.mkv', 'is_dir': False},
        {'name': 'another.mkv', 'is_dir': False}
    ]
    mocker.patch.object(sftp, '_list_remote_files_recursive_helper', side_effect=lambda path, entries: entries.extend(mock_entries))
    
    # Mock os.path.abspath to return short paths
    mocker.patch('os.path.abspath', return_value="/short/path")
    
    result = sftp._truncate_for_windows_path("/base", "dir", "/remote", 250)
    
    assert result[0] == "dir"  # No truncation
    assert result[1] is None   # No filename map

def test_truncate_for_windows_path_dir_truncation_needed(mocker):
    """Test path truncation when directory name needs truncation."""
    sftp = create_sftp_with_mock_client(mocker)
    sftp.llm_service = mocker.Mock()
    sftp.llm_service.suggest_short_dirname.return_value = "short_dir"
    
    # Mock _list_remote_files_recursive_helper to return short filenames
    mock_entries = [
        {'name': 'short.mkv', 'is_dir': False},
        {'name': 'another.mkv', 'is_dir': False}
    ]
    mocker.patch.object(sftp, '_list_remote_files_recursive_helper', side_effect=lambda path, entries: entries.extend(mock_entries))
    
    # Mock os.path.abspath to return long paths initially, then short after truncation
    def mock_abspath(path):
        if "very_long_directory_name" in path:
            return "x" * 300  # Too long
        return "/short/path"
    
    mocker.patch('os.path.abspath', side_effect=mock_abspath)
    
    result = sftp._truncate_for_windows_path("/base", "very_long_directory_name", "/remote", 250)
    
    assert result[0] == "short_dir"  # Truncated
    assert result[1] is None         # No filename map needed

def test_truncate_for_windows_path_filename_truncation_needed(mocker):
    """Test path truncation when filenames need truncation."""
    sftp = create_sftp_with_mock_client(mocker)
    sftp.llm_service = mocker.Mock()
    sftp.llm_service.suggest_short_dirname.return_value = "short_dir"
    sftp.llm_service.suggest_short_filename.return_value = "short.mkv"
    
    # Mock _list_remote_files_recursive_helper to return long filenames
    mock_entries = [
        {'name': 'very_long_filename_that_needs_truncation.mkv', 'is_dir': False},
        {'name': 'another_very_long_filename.mkv', 'is_dir': False}
    ]
    mocker.patch.object(sftp, '_list_remote_files_recursive_helper', side_effect=lambda path, entries: entries.extend(mock_entries))
    
    # Mock os.path.abspath to always return long paths
    mocker.patch('os.path.abspath', return_value="x" * 300)
    
    # Mock _truncate_filename
    mocker.patch.object(sftp, '_truncate_filename', return_value="truncated.mkv")
    
    result = sftp._truncate_for_windows_path("/base", "dir", "/remote", 250)
    
    assert result[0] == "short_dir"  # Truncated
    assert result[1] is not None     # Filename map created
    assert len(result[1]) == 2       # Two files mapped

# ─────────────────────────────────────────────────────────
# Download Method Tests
# ─────────────────────────────────────────────────────────

def test_download_file_with_path_truncation(mocker, tmp_path):
    """Test download_file with path length truncation."""
    sftp = create_sftp_with_mock_client(mocker)
    sftp.llm_service = mocker.Mock()
    sftp.llm_service.suggest_short_filename.return_value = "short.mkv"
    
    # Create a path that's too long
    long_path = tmp_path / ("x" * 200) / "very_long_filename_that_needs_truncation.mkv"
    
    # Mock os.path.abspath to return a path that's too long initially
    def mock_abspath(path):
        if "very_long_filename_that_needs_truncation.mkv" in str(path):
            return "x" * 300  # Too long
        return str(path)
    
    mocker.patch('os.path.abspath', side_effect=mock_abspath)
    
    # Mock _truncate_filename
    mocker.patch.object(sftp, '_truncate_filename', return_value="short.mkv")
    
    sftp.download_file("/remote/file.mkv", str(long_path))
    
    # Should call _truncate_filename
    sftp._truncate_filename.assert_called_once()

def test_download_file_skips_after_truncation_still_too_long(mocker, tmp_path):
    """Test download_file skips file when path is still too long after truncation."""
    sftp = create_sftp_with_mock_client(mocker)
    
    # Create a path that's too long
    long_path = tmp_path / ("x" * 200) / "very_long_filename.mkv"
    
    # Mock os.path.abspath to always return a path that's too long
    mocker.patch('os.path.abspath', return_value="x" * 300)
    
    # Mock _truncate_filename
    mocker.patch.object(sftp, '_truncate_filename', return_value="still_too_long.mkv")
    
    sftp.download_file("/remote/file.mkv", str(long_path))
    
    # Should not call client.get because path is still too long
    sftp.client.get.assert_not_called()

def test_download_file_success(mocker, tmp_path):
    sftp = create_sftp_with_mock_client(mocker)
    remote_path = "/remote/file.mkv"
    local_path = tmp_path / "file.mkv"

    sftp.download_file(remote_path, str(local_path))
    sftp.client.get.assert_called_once_with(remote_path, str(local_path))

def test_download_dir_with_filename_mapping(mocker, tmp_path, mock_sftp_attr):
    """Test download_dir with filename mapping."""
    sftp = create_sftp_with_mock_client(mocker)
    remote_root = "/remote"
    local_root = tmp_path / "downloads"
    
    # Provide filename mapping
    filename_map = {"original.mkv": "mapped.mkv"}
    
    file_attr = mock_sftp_attr("original.mkv", 1000, (datetime.now() - timedelta(minutes=5)).timestamp())
    
    sftp.client.listdir_attr.return_value = [file_attr]
    
    # Mock the file filter functions to always return True
    mocker.patch('services.sftp_service.is_valid_media_file', return_value=True)
    mocker.patch('services.sftp_service.is_valid_directory', return_value=True)
    
    # Mock the ThreadPoolExecutor to avoid actual threading
    mock_executor = mocker.Mock()
    mock_future = mocker.Mock()
    mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
    mock_executor.submit.return_value = mock_future
    mock_executor.__exit__ = mocker.Mock(return_value=None)
    mocker.patch('services.sftp_service.ThreadPoolExecutor', return_value=mock_executor)
    
    # Mock as_completed to return the future to simulate completion
    mocker.patch('services.sftp_service.as_completed', return_value=[mock_future])
    
    # Mock the future.result() to avoid any exceptions
    mock_future.result.return_value = None

    # Mock the new SFTPService instances that will be created
    mock_new_sftp = mocker.Mock()
    mock_new_sftp.__enter__ = mocker.Mock(return_value=mock_new_sftp)
    mock_new_sftp.__exit__ = mocker.Mock(return_value=None)
    mock_new_sftp.download_file = mocker.Mock()
    mocker.patch('services.sftp_service.SFTPService', return_value=mock_new_sftp)

    sftp.download_dir(remote_root, str(local_root), filename_map=filename_map)

    # Verify that the executor was called with the expected task
    assert mock_executor.submit.call_count == 1

def test_download_dir_with_subdirectory_filtering(mocker, tmp_path, mock_sftp_attr):
    """Test download_dir filters out invalid directories."""
    sftp = create_sftp_with_mock_client(mocker)
    remote_root = "/remote"
    local_root = tmp_path / "downloads"
    
    dir_attr = mock_sftp_attr("invalid_dir", 0, (datetime.now() - timedelta(minutes=5)).timestamp(), is_dir=True)
    
    sftp.client.listdir_attr.return_value = [dir_attr]
    
    # Mock the file filter functions
    mocker.patch('services.sftp_service.is_valid_media_file', return_value=True)
    mocker.patch('services.sftp_service.is_valid_directory', return_value=False)  # Invalid directory
    
    # Mock the truncation method to avoid recursive calls
    mocker.patch.object(sftp, '_truncate_for_windows_path', return_value=('invalid_dir', None))
    
    # Mock the ThreadPoolExecutor to avoid actual threading
    mock_executor = mocker.Mock()
    mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
    mock_executor.submit.return_value = mocker.Mock()
    mock_executor.__exit__ = mocker.Mock(return_value=None)
    mocker.patch('services.sftp_service.ThreadPoolExecutor', return_value=mock_executor)

    sftp.download_dir(remote_root, str(local_root))

    # Should not submit any tasks because directory was filtered out
    mock_executor.submit.assert_not_called()

def test_download_dir_with_file_filtering(mocker, tmp_path, mock_sftp_attr):
    """Test download_dir filters out invalid files."""
    sftp = create_sftp_with_mock_client(mocker)
    remote_root = "/remote"
    local_root = tmp_path / "downloads"
    
    file_attr = mock_sftp_attr("invalid_file.txt", 1000, (datetime.now() - timedelta(minutes=5)).timestamp())
    
    sftp.client.listdir_attr.return_value = [file_attr]
    
    # Mock the file filter functions
    mocker.patch('services.sftp_service.is_valid_media_file', return_value=False)  # Invalid file
    mocker.patch('services.sftp_service.is_valid_directory', return_value=True)
    
    # Mock the truncation method to avoid recursive calls
    mocker.patch.object(sftp, '_truncate_for_windows_path', return_value=('dir', None))
    
    # Mock the ThreadPoolExecutor to avoid actual threading
    mock_executor = mocker.Mock()
    mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
    mock_executor.submit.return_value = mocker.Mock()
    mock_executor.__exit__ = mocker.Mock(return_value=None)
    mocker.patch('services.sftp_service.ThreadPoolExecutor', return_value=mock_executor)

    sftp.download_dir(remote_root, str(local_root))

    # Should not submit any tasks because file was filtered out
    mock_executor.submit.assert_not_called()

def test_download_dir_with_exception_handling(mocker, tmp_path, mock_sftp_attr):
    """Test download_dir handles exceptions from thread pool tasks."""
    sftp = create_sftp_with_mock_client(mocker)
    remote_root = "/remote"
    local_root = tmp_path / "downloads"
    
    file_attr = mock_sftp_attr("file.mkv", 1000, (datetime.now() - timedelta(minutes=5)).timestamp())
    
    sftp.client.listdir_attr.return_value = [file_attr]
    
    # Mock the file filter functions to always return True
    mocker.patch('services.sftp_service.is_valid_media_file', return_value=True)
    mocker.patch('services.sftp_service.is_valid_directory', return_value=True)
    
    # Mock the truncation method to avoid recursive calls
    mocker.patch.object(sftp, '_truncate_for_windows_path', return_value=('dir', None))
    
    # Mock the ThreadPoolExecutor to avoid actual threading
    mock_executor = mocker.Mock()
    mock_future = mocker.Mock()
    mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
    mock_executor.submit.return_value = mock_future
    mock_executor.__exit__ = mocker.Mock(return_value=None)
    mocker.patch('services.sftp_service.ThreadPoolExecutor', return_value=mock_executor)
    
    # Mock as_completed to return the future to simulate completion
    mocker.patch('services.sftp_service.as_completed', return_value=[mock_future])
    
    # Mock the future.result() to raise an exception
    mock_future.result.side_effect = Exception("Download failed")

    # Mock the new SFTPService instances that will be created
    mock_new_sftp = mocker.Mock()
    mock_new_sftp.__enter__ = mocker.Mock(return_value=mock_new_sftp)
    mock_new_sftp.__exit__ = mocker.Mock(return_value=None)
    mock_new_sftp.download_file = mocker.Mock()
    mocker.patch('services.sftp_service.SFTPService', return_value=mock_new_sftp)

    # Should not raise exception, should log it
    sftp.download_dir(remote_root, str(local_root))

    # Verify that the executor was called
    assert mock_executor.submit.call_count == 1

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

def test_download_dir_success(mocker, tmp_path, mock_sftp_attr):
    sftp = create_sftp_with_mock_client(mocker)
    remote_root = "/remote"
    local_root = tmp_path / "downloads"

    file_attr = mock_sftp_attr("file1.mkv", 1000, (datetime.now() - timedelta(minutes=5)).timestamp())
    dir_attr = mock_sftp_attr("subdir", 0, (datetime.now() - timedelta(minutes=5)).timestamp(), is_dir=True)
    subfile_attr = mock_sftp_attr("file2.mkv", 500, (datetime.now() - timedelta(minutes=5)).timestamp())

    sftp.client.listdir_attr.side_effect = [
        [file_attr, dir_attr],
        [subfile_attr],
        []  # Add empty list to prevent StopIteration
    ]

    # Mock the file filter functions to always return True
    mocker.patch('services.sftp_service.is_valid_media_file', return_value=True)
    mocker.patch('services.sftp_service.is_valid_directory', return_value=True)
    
    # Mock the truncation method to avoid recursive calls
    mocker.patch.object(sftp, '_truncate_for_windows_path', return_value=('subdir', None))
    
    # Mock the ThreadPoolExecutor to avoid actual threading
    mock_executor = mocker.Mock()
    mock_future = mocker.Mock()
    mock_executor.__enter__ = mocker.Mock(return_value=mock_executor)
    mock_executor.submit.return_value = mock_future
    mock_executor.__exit__ = mocker.Mock(return_value=None)
    mocker.patch('services.sftp_service.ThreadPoolExecutor', return_value=mock_executor)
    
    # Mock as_completed to return the future to simulate completion
    mocker.patch('services.sftp_service.as_completed', return_value=[mock_future])
    
    # Mock the future.result() to avoid any exceptions
    mock_future.result.return_value = None

    # Mock the new SFTPService instances that will be created
    mock_new_sftp = mocker.Mock()
    mock_new_sftp.__enter__ = mocker.Mock(return_value=mock_new_sftp)
    mock_new_sftp.__exit__ = mocker.Mock(return_value=None)
    mock_new_sftp.download_file = mocker.Mock()
    mock_new_sftp.download_dir = mocker.Mock()
    mock_new_sftp.client = mocker.Mock()
    mock_new_sftp.client.get = mocker.Mock()
    mocker.patch('services.sftp_service.SFTPService', return_value=mock_new_sftp)

    sftp.download_dir(remote_root, str(local_root))

    # Verify that the executor was called with the expected tasks
    assert mock_executor.submit.call_count == 2
