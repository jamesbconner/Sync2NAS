import pytest
from unittest.mock import MagicMock
from api.services.show_service import ShowService

import asyncio

def asyncio_run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- add_show ---
def test_add_show_success(mocker):
    """Test that add_show returns success and correct data when show is added successfully."""
    db = MagicMock()
    tmdb = MagicMock()
    mock_result = {"tmdb_name": "Test Show", "sys_path": "/shows/Test Show", "episode_count": 10}
    mocker.patch("api.services.show_service.add_show_interactively", return_value=mock_result)
    service = ShowService(db, tmdb, "/shows")
    result = asyncio_run(service.add_show(show_name="Test Show"))
    assert result["success"] is True
    assert result["tmdb_name"] == "Test Show"
    assert result["episode_count"] == 10
    assert "Show added successfully" in result["message"]

def test_add_show_missing_params(mocker):
    """Test that add_show raises ValueError if neither show_name nor tmdb_id is provided."""
    db = MagicMock()
    tmdb = MagicMock()
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(ValueError):
        asyncio_run(service.add_show())

def test_add_show_exists(mocker):
    """Test that add_show raises FileExistsError if the show already exists and override_dir is False."""
    db = MagicMock()
    tmdb = MagicMock()
    mocker.patch("api.services.show_service.add_show_interactively", side_effect=FileExistsError("exists"))
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(FileExistsError):
        asyncio_run(service.add_show(show_name="Test Show"))

def test_add_show_unexpected_error(mocker):
    """Test that add_show raises Exception for unexpected errors."""
    db = MagicMock()
    tmdb = MagicMock()
    mocker.patch("api.services.show_service.add_show_interactively", side_effect=Exception("fail"))
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(Exception):
        asyncio_run(service.add_show(show_name="Test Show"))

# --- get_shows ---
def test_get_shows_success():
    """Test that get_shows returns a list of shows from the database."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_all_shows.return_value = [
        {"id": 1, "tmdb_id": 123, "tmdb_name": "Test Show", "sys_name": "Test_Show", "sys_path": "/shows/Test_Show", "aliases": ["Alias"]}
    ]
    service = ShowService(db, tmdb, "/shows")
    result = asyncio_run(service.get_shows())
    assert isinstance(result, list)
    assert result[0]["tmdb_name"] == "Test Show"
    assert result[0]["aliases"] == ["Alias"]

def test_get_shows_db_error():
    """Test that get_shows raises Exception if the database call fails."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_all_shows.side_effect = Exception("db fail")
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(Exception):
        asyncio_run(service.get_shows())

# --- get_show ---
def test_get_show_success():
    """Test that get_show returns the correct show dictionary when found."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_id.return_value = {"id": 1, "tmdb_id": 123, "tmdb_name": "Test Show", "sys_name": "Test_Show", "sys_path": "/shows/Test_Show", "aliases": None}
    service = ShowService(db, tmdb, "/shows")
    result = asyncio_run(service.get_show(1))
    assert result["tmdb_name"] == "Test Show"

def test_get_show_not_found():
    """Test that get_show returns None if the show is not found in the database."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_id.return_value = None
    service = ShowService(db, tmdb, "/shows")
    result = asyncio_run(service.get_show(1))
    assert result is None

def test_get_show_db_error():
    """Test that get_show raises Exception if the database call fails."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_id.side_effect = Exception("db fail")
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(Exception):
        asyncio_run(service.get_show(1))

# --- update_episodes ---
def test_update_episodes_success_tmdb_id(mocker):
    """Test that update_episodes returns success and correct data when updating by tmdb_id."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_tmdb_id.return_value = {"id": 1, "tmdb_id": 123, "tmdb_name": "Test Show", "sys_name": "Test_Show", "sys_path": "/shows/Test_Show"}
    mock_show = MagicMock()
    mock_show.sys_name = "Test_Show"
    mocker.patch("api.services.show_service.Show.from_db_record", return_value=mock_show)
    mocker.patch("api.services.show_service.refresh_episodes_for_show", return_value=5)
    service = ShowService(db, tmdb, "/shows")
    result = asyncio_run(service.update_episodes(tmdb_id=123))
    assert result["success"] is True
    assert result["episodes_updated"] == 5
    assert result["show_name"] == "Test_Show"

def test_update_episodes_success_show_name(mocker):
    """Test that update_episodes returns success and correct data when updating by show_name."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_name_or_alias.return_value = {"id": 1, "tmdb_id": 123, "tmdb_name": "Test Show", "sys_name": "Test_Show", "sys_path": "/shows/Test_Show"}
    mock_show = MagicMock()
    mock_show.sys_name = "Test_Show"
    mocker.patch("api.services.show_service.Show.from_db_record", return_value=mock_show)
    mocker.patch("api.services.show_service.refresh_episodes_for_show", return_value=3)
    service = ShowService(db, tmdb, "/shows")
    result = asyncio_run(service.update_episodes(show_name="Test Show"))
    assert result["success"] is True
    assert result["episodes_updated"] == 3
    assert result["show_name"] == "Test_Show"

def test_update_episodes_missing_params():
    """Test that update_episodes raises ValueError if neither show_name nor tmdb_id is provided."""
    db = MagicMock()
    tmdb = MagicMock()
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(ValueError):
        asyncio_run(service.update_episodes())

def test_update_episodes_show_not_found_tmdb_id():
    """Test that update_episodes raises ValueError if no show is found for the given tmdb_id."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_tmdb_id.return_value = None
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(ValueError):
        asyncio_run(service.update_episodes(tmdb_id=123))

def test_update_episodes_show_not_found_show_name():
    """Test that update_episodes raises ValueError if no show is found for the given show_name."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_name_or_alias.return_value = None
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(ValueError):
        asyncio_run(service.update_episodes(show_name="Test Show"))

def test_update_episodes_no_episodes(mocker):
    """Test that update_episodes raises ValueError if no episodes are updated (refresh returns 0)."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_tmdb_id.return_value = {"id": 1, "tmdb_id": 123, "tmdb_name": "Test Show", "sys_name": "Test_Show", "sys_path": "/shows/Test_Show"}
    mock_show = MagicMock()
    mocker.patch("api.services.show_service.Show.from_db_record", return_value=mock_show)
    mocker.patch("api.services.show_service.refresh_episodes_for_show", return_value=0)
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(ValueError):
        asyncio_run(service.update_episodes(tmdb_id=123))

def test_update_episodes_unexpected_error(mocker):
    """Test that update_episodes raises Exception for unexpected errors during refresh."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_tmdb_id.return_value = {"id": 1, "tmdb_id": 123, "tmdb_name": "Test Show", "sys_name": "Test_Show", "sys_path": "/shows/Test_Show"}
    mock_show = MagicMock()
    mocker.patch("api.services.show_service.Show.from_db_record", return_value=mock_show)
    mocker.patch("api.services.show_service.refresh_episodes_for_show", side_effect=Exception("fail"))
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(Exception):
        asyncio_run(service.update_episodes(tmdb_id=123))

# --- delete_show ---
def test_delete_show_success():
    """Test that delete_show returns success and correct data when a show is deleted."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_id.return_value = {"id": 1, "tmdb_id": 123, "tmdb_name": "Test Show", "sys_name": "Test_Show", "sys_path": "/shows/Test_Show"}
    db.get_episodes_by_tmdb_id.return_value = [{}, {}, {}]
    service = ShowService(db, tmdb, "/shows")
    result = asyncio_run(service.delete_show(1))
    assert result["success"] is True
    assert result["show_name"] == "Test Show"
    assert result["episodes_deleted"] == 3

def test_delete_show_not_found():
    """Test that delete_show raises ValueError if the show is not found in the database."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_id.return_value = None
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(ValueError):
        asyncio_run(service.delete_show(1))

def test_delete_show_unexpected_error():
    """Test that delete_show raises Exception for unexpected errors during deletion."""
    db = MagicMock()
    tmdb = MagicMock()
    db.get_show_by_id.side_effect = Exception("fail")
    service = ShowService(db, tmdb, "/shows")
    with pytest.raises(Exception):
        asyncio_run(service.delete_show(1)) 