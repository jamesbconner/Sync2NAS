import pytest
import os
from unittest.mock import MagicMock
from api.services.admin_service import AdminService

@pytest.fixture
def temp_anime_tv_path(tmp_path):
    anime_tv_path = tmp_path / "anime_tv"
    anime_tv_path.mkdir()
    return str(anime_tv_path)

# Helper for running async methods in pytest
import asyncio
def asyncio_run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def test_bootstrap_tv_shows_success(db_service, mock_tmdb_service, temp_anime_tv_path, mocker):
    """Test that bootstrap_tv_shows adds new shows and skips existing ones."""
    # Simulate two folders: one new, one already exists
    os.makedirs(os.path.join(temp_anime_tv_path, "Show1"))
    os.makedirs(os.path.join(temp_anime_tv_path, "Show2"))
    mocker.patch("os.listdir", return_value=["Show1", "Show2"])
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch.object(db_service, "show_exists", side_effect=[False, True])
    mocker.patch.object(db_service, "add_show", return_value=None)
    show_mock = MagicMock()
    show_mock.tmdb_name = "Show1"
    show_mock.sys_name = "Show1"
    mocker.patch("api.services.admin_service.Show.from_tmdb", return_value=show_mock)
    mocker.patch.object(mock_tmdb_service, "search_show", return_value={"results": [{"id": 1}]})
    mocker.patch.object(mock_tmdb_service, "get_show_details", return_value={"info": {}})
    admin_service = AdminService(db_service, mock_tmdb_service, temp_anime_tv_path, {})
    result = asyncio_run(admin_service.bootstrap_tv_shows(dry_run=False))
    assert result["success"] is True
    assert result["added"] == 1
    assert result["skipped"] == 1
    assert result["failed"] == 0


def test_bootstrap_tv_shows_tmdb_fail(db_service, mock_tmdb_service, temp_anime_tv_path, mocker):
    """Test that bootstrap_tv_shows counts as failed if TMDB search returns no results."""
    os.makedirs(os.path.join(temp_anime_tv_path, "Show1"))
    mocker.patch("os.listdir", return_value=["Show1"])
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch.object(db_service, "show_exists", return_value=False)
    mocker.patch.object(mock_tmdb_service, "search_show", return_value={"results": []})
    admin_service = AdminService(db_service, mock_tmdb_service, temp_anime_tv_path, {})
    result = asyncio_run(admin_service.bootstrap_tv_shows(dry_run=False))
    assert result["failed"] == 1
    assert result["added"] == 0


def test_bootstrap_tv_shows_exception(db_service, mock_tmdb_service, temp_anime_tv_path, mocker):
    """Test that bootstrap_tv_shows counts as failed if TMDB search raises an exception."""
    os.makedirs(os.path.join(temp_anime_tv_path, "Show1"))
    mocker.patch("os.listdir", return_value=["Show1"])
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch.object(db_service, "show_exists", return_value=False)
    mocker.patch.object(mock_tmdb_service, "search_show", side_effect=Exception("fail!"))
    admin_service = AdminService(db_service, mock_tmdb_service, temp_anime_tv_path, {})
    result = asyncio_run(admin_service.bootstrap_tv_shows(dry_run=False))
    assert result["failed"] == 1
    assert result["added"] == 0


def test_bootstrap_episodes_success(db_service, mock_tmdb_service, temp_anime_tv_path, mocker):
    """Test that bootstrap_episodes adds episodes for shows with no episodes and skips those with episodes."""
    # Simulate two shows: one with no episodes, one already has episodes
    show1 = MagicMock()
    show1.sys_name = "Show1"
    show1.tmdb_id = 1
    show1.id = 1
    show2 = MagicMock()
    show2.sys_name = "Show2"
    show2.tmdb_id = 2
    show2.id = 2
    mocker.patch.object(db_service, "get_all_shows", return_value=[{"sys_name": "Show1", "tmdb_id": 1, "id": 1}, {"sys_name": "Show2", "tmdb_id": 2, "id": 2}])
    mocker.patch("api.services.admin_service.Show.from_db_record", side_effect=[show1, show2])
    mocker.patch.object(db_service, "get_episodes_by_tmdb_id", side_effect=[[], [1, 2]])
    mock_tmdb_service.get_show_episodes = MagicMock(return_value=[{"ep": 1}])
    mocker.patch("models.episode.Episode.parse_from_tmdb", return_value=MagicMock())
    mocker.patch.object(db_service, "add_episode", return_value=None)
    admin_service = AdminService(db_service, mock_tmdb_service, temp_anime_tv_path, {})
    result = asyncio_run(admin_service.bootstrap_episodes(dry_run=False))
    assert result["success"] is True
    assert result["added"] == 1
    assert result["skipped"] == 1
    assert result["failed"] == 0


def test_bootstrap_episodes_tmdb_fail(db_service, mock_tmdb_service, temp_anime_tv_path, mocker):
    """Test that bootstrap_episodes counts as failed if TMDB returns no episodes."""
    show1 = MagicMock()
    show1.sys_name = "Show1"
    show1.tmdb_id = 1
    show1.id = 1
    mocker.patch.object(db_service, "get_all_shows", return_value=[{"sys_name": "Show1", "tmdb_id": 1, "id": 1}])
    mocker.patch("api.services.admin_service.Show.from_db_record", return_value=show1)
    mocker.patch.object(db_service, "get_episodes_by_tmdb_id", return_value=[])
    mock_tmdb_service.get_show_episodes = MagicMock(return_value=None)
    admin_service = AdminService(db_service, mock_tmdb_service, temp_anime_tv_path, {})
    result = asyncio_run(admin_service.bootstrap_episodes(dry_run=False))
    assert result["failed"] == 1
    assert result["added"] == 0


def test_bootstrap_episodes_exception(db_service, mock_tmdb_service, temp_anime_tv_path, mocker):
    """Test that bootstrap_episodes counts as failed if TMDB get_show_episodes raises an exception."""
    show1 = MagicMock()
    show1.sys_name = "Show1"
    show1.tmdb_id = 1
    show1.id = 1
    mocker.patch.object(db_service, "get_all_shows", return_value=[{"sys_name": "Show1", "tmdb_id": 1, "id": 1}])
    mocker.patch("api.services.admin_service.Show.from_db_record", return_value=show1)
    mocker.patch.object(db_service, "get_episodes_by_tmdb_id", return_value=[])
    mock_tmdb_service.get_show_episodes = MagicMock(side_effect=Exception("fail!"))
    admin_service = AdminService(db_service, mock_tmdb_service, temp_anime_tv_path, {})
    result = asyncio_run(admin_service.bootstrap_episodes(dry_run=False))
    assert result["failed"] == 1
    assert result["added"] == 0


def test_backup_database_success(db_service, mock_tmdb_service, temp_anime_tv_path):
    """Test that backup_database returns success and includes backup_path in the result."""
    admin_service = AdminService(db_service, mock_tmdb_service, temp_anime_tv_path, {})
    result = asyncio_run(admin_service.backup_database())
    assert result["success"] is True
    assert "backup_path" in result


def test_init_database_success(db_service, mock_tmdb_service, temp_anime_tv_path):
    """Test that init_database returns success and includes 'initialized' in the message."""
    admin_service = AdminService(db_service, mock_tmdb_service, temp_anime_tv_path, {})
    result = asyncio_run(admin_service.init_database())
    assert result["success"] is True
    assert "initialized" in result["message"].lower() 