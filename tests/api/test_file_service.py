import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from api.services.file_service import FileService

@pytest.fixture
def temp_dirs(tmp_path):
    anime_tv_path = tmp_path / "anime_tv"
    incoming_path = tmp_path / "incoming"
    anime_tv_path.mkdir()
    incoming_path.mkdir()
    return str(anime_tv_path), str(incoming_path)


def test_route_files_success(db_service, mock_tmdb_service, temp_dirs, mocker):
    """Test that route_files returns success and correct file info when routing is successful."""
    anime_tv_path, incoming_path = temp_dirs
    file_service = FileService(db_service, mock_tmdb_service, anime_tv_path, incoming_path)
    fake_routed = [
        {
            "original_path": "/incoming/file1.mkv",
            "routed_path": "/anime_tv/Show/Season 01/file1.mkv",
            "show_name": "Show",
            "season": 1,
            "episode": 1
        }
    ]
    mock_file_routing = mocker.patch("api.services.file_service.file_routing", return_value=fake_routed)
    result = asyncio_run(file_service.route_files())
    assert result["success"] is True
    assert result["files_routed"] == 1
    assert result["files"][0]["show_name"] == "Show"
    mock_file_routing.assert_called_once()


def test_route_files_auto_add(db_service, mock_tmdb_service, temp_dirs, mocker):
    """Test that route_files calls _auto_add_missing_shows when auto_add=True."""
    anime_tv_path, incoming_path = temp_dirs
    file_service = FileService(db_service, mock_tmdb_service, anime_tv_path, incoming_path)
    mock_auto_add = mocker.patch.object(file_service, "_auto_add_missing_shows", return_value=None)
    mock_file_routing = mocker.patch("api.services.file_service.file_routing", return_value=[])
    result = asyncio_run(file_service.route_files(auto_add=True))
    mock_auto_add.assert_called_once_with(False)
    mock_file_routing.assert_called_once()
    assert result["success"] is True


def test_route_files_exception(db_service, mock_tmdb_service, temp_dirs, mocker):
    """Test that route_files raises Exception if file_routing fails."""
    anime_tv_path, incoming_path = temp_dirs
    file_service = FileService(db_service, mock_tmdb_service, anime_tv_path, incoming_path)
    mocker.patch("api.services.file_service.file_routing", side_effect=Exception("fail!"))
    with pytest.raises(Exception) as exc:
        asyncio_run(file_service.route_files())
    assert "fail!" in str(exc.value)


def test_list_incoming_files_success(db_service, mock_tmdb_service, temp_dirs, mocker):
    """Test that list_incoming_files returns success and correct file info for files in incoming directory."""
    anime_tv_path, incoming_path = temp_dirs
    file_service = FileService(db_service, mock_tmdb_service, anime_tv_path, incoming_path)
    test_file = os.path.join(incoming_path, "test.mkv")
    with open(test_file, "w") as f:
        f.write("data")
    result = asyncio_run(file_service.list_incoming_files())
    assert result["success"] is True
    assert result["count"] == 1
    assert result["files"][0]["name"] == "test.mkv"


def test_list_incoming_files_exception(db_service, mock_tmdb_service, temp_dirs, mocker):
    """Test that list_incoming_files raises Exception if os.walk fails."""
    anime_tv_path, incoming_path = temp_dirs
    file_service = FileService(db_service, mock_tmdb_service, anime_tv_path, incoming_path)
    mocker.patch("os.walk", side_effect=Exception("failwalk"))
    with pytest.raises(Exception) as exc:
        asyncio_run(file_service.list_incoming_files())
    assert "failwalk" in str(exc.value)


def test__auto_add_missing_shows_adds_new_show(db_service, mock_tmdb_service, temp_dirs, mocker):
    """Test that _auto_add_missing_shows calls add_show_interactively for new shows."""
    anime_tv_path, incoming_path = temp_dirs
    file_service = FileService(db_service, mock_tmdb_service, anime_tv_path, incoming_path)
    test_file = os.path.join(incoming_path, "newshow.mkv")
    with open(test_file, "w") as f:
        f.write("data")
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("api.services.file_service.parse_filename", return_value={"show_name": "NewShow", "season": 1, "episode": 1})
    mocker.patch.object(db_service, "show_exists", return_value=False)
    mock_add_show = mocker.patch("api.services.file_service.add_show_interactively", return_value=None)
    asyncio_run(file_service._auto_add_missing_shows(dry_run=False))
    mock_add_show.assert_called_once()


def test__auto_add_missing_shows_skips_existing_show(db_service, mock_tmdb_service, temp_dirs, mocker):
    """Test that _auto_add_missing_shows does not call add_show_interactively for existing shows."""
    anime_tv_path, incoming_path = temp_dirs
    file_service = FileService(db_service, mock_tmdb_service, anime_tv_path, incoming_path)
    test_file = os.path.join(incoming_path, "existingshow.mkv")
    with open(test_file, "w") as f:
        f.write("data")
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("api.services.file_service.parse_filename", return_value={"show_name": "ExistingShow", "season": 1, "episode": 1})
    mocker.patch.object(db_service, "show_exists", return_value=True)
    mock_add_show = mocker.patch("api.services.file_service.add_show_interactively", return_value=None)
    asyncio_run(file_service._auto_add_missing_shows(dry_run=False))
    mock_add_show.assert_not_called()

# Helper for running async methods in pytest
import asyncio
def asyncio_run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def test_file_service_basic():
    """Basic placeholder test for api/services/file_service.py functionality."""
    # TODO: Add tests for api/services/file_service.py
    assert True 