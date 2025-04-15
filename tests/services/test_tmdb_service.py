import pytest
from unittest.mock import patch
from services.tmdb_service import TMDBService

def test_search_show(mock_tmdb_service):
    results = mock_tmdb_service.search_show("Mock Show")
    assert results is not None
    assert "results" in results
    assert results["results"][0]["name"] == "Mock Show"

def test_get_show_details(mock_tmdb_service):
    details = mock_tmdb_service.get_show_details(123)
    assert "info" in details
    assert details["info"]["name"] == "Mock Show"

def test_get_show_season_details(mock_tmdb_service):
    season = mock_tmdb_service.get_show_season_details(123, 1)
    assert "episodes" in season
    assert season["episodes"][0]["episode_number"] == 1

def test_get_show_episode_details(mock_tmdb_service):
    episode = mock_tmdb_service.get_show_episode_details(123, 1, 1)
    assert episode["episode_number"] == 1

def test_get_episode_group_details(mock_tmdb_service):
    mock_tmdb_service.get_episode_group_details.return_value = {
        "id": "abc", "groups": [], "type": 6
    }
    group = mock_tmdb_service.get_episode_group_details("abc")
    assert group["id"] == "abc"

# Edge cases
def test_search_show_returns_empty_results(mock_tmdb_service):
    mock_tmdb_service.search_show.return_value = {"results": []}
    result = mock_tmdb_service.search_show("NoSuchShow")
    assert isinstance(result, dict)
    assert result["results"] == []

def test_get_show_details_missing_fields(mock_tmdb_service):
    mock_tmdb_service.get_show_details.return_value = {}
    result = mock_tmdb_service.get_show_details(999999)
    assert result == {}

def test_get_show_season_details_empty(mock_tmdb_service):
    mock_tmdb_service.get_show_season_details.return_value = {"episodes": []}
    result = mock_tmdb_service.get_show_season_details(123, 1)
    assert result["episodes"] == []

def test_get_show_episode_details_returns_none(mock_tmdb_service):
    with patch.object(mock_tmdb_service, "get_show_episode_details", return_value=None):
        result = mock_tmdb_service.get_show_episode_details(123, 1, 1)
        assert result is None