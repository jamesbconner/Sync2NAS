# tests/services/test_tmdb_service.py

import pytest
from unittest.mock import patch
import requests
from services.tmdb_service import TMDBService

# ────────────────────────────────────────────────
# FIXTURES
# ────────────────────────────────────────────────

@pytest.fixture
def tmdb_service():
    """Fixture for creating a TMDBService instance with a dummy API key."""
    return TMDBService("dummy_api_key")


# ────────────────────────────────────────────────
# SEARCH SHOW TESTS
# ────────────────────────────────────────────────

def test_search_show_success(tmdb_service):
    mock_response = {
        "results": [{"name": "Mock Show", "id": 123}]
    }
    with patch('tmdbsimple.Search.tv', return_value=mock_response):
        result = tmdb_service.search_show("Mock Show")
        assert result is not None
        assert isinstance(result, dict)
        assert result["results"][0]["name"] == "Mock Show"

def test_search_show_http_error(tmdb_service):
    with patch('tmdbsimple.Search.tv', side_effect=requests.exceptions.HTTPError):
        result = tmdb_service.search_show("Error Show")
        assert result is None

def test_search_show_general_error(tmdb_service):
    with patch('tmdbsimple.Search.tv', side_effect=Exception("General error")):
        with pytest.raises(Exception, match="General error"):
            tmdb_service.search_show("Error Show")

def test_search_show_empty_results(tmdb_service):
    with patch('tmdbsimple.Search.tv', return_value={"results": []}):
        result = tmdb_service.search_show("NoSuchShow")
        assert isinstance(result, dict)
        assert result["results"] == []


# ────────────────────────────────────────────────
# GET SHOW DETAILS TESTS
# ────────────────────────────────────────────────

def test_get_show_details_success(tmdb_service):
    mock_info = {"name": "Mock Show", "id": 123}
    mock_episode_groups = {"results": []}
    mock_alternative_titles = {"results": []}
    mock_external_ids = {"imdb_id": "tt1234567"}

    with patch('tmdbsimple.TV.info', return_value=mock_info), \
         patch('tmdbsimple.TV.episode_groups', return_value=mock_episode_groups), \
         patch('tmdbsimple.TV.alternative_titles', return_value=mock_alternative_titles), \
         patch('tmdbsimple.TV.external_ids', return_value=mock_external_ids):

        result = tmdb_service.get_show_details(123)
        assert result["info"]["name"] == "Mock Show"
        assert result["episode_groups"]["results"] == []
        assert result["alternative_titles"]["results"] == []
        assert result["external_ids"]["imdb_id"] == "tt1234567"

def test_get_show_details_http_error(tmdb_service):
    with patch('tmdbsimple.TV.info', side_effect=requests.exceptions.HTTPError):
        result = tmdb_service.get_show_details(123)
        assert result is None

def test_get_show_details_general_error(tmdb_service):
    with patch('tmdbsimple.TV.info', side_effect=Exception("General error")):
        with pytest.raises(Exception, match="General error"):
            tmdb_service.get_show_details(123)

def test_get_show_details_missing_fields(tmdb_service):
    with patch('tmdbsimple.TV.info', return_value={}), \
         patch('tmdbsimple.TV.episode_groups', return_value={"results": []}), \
         patch('tmdbsimple.TV.alternative_titles', return_value={"results": []}), \
         patch('tmdbsimple.TV.external_ids', return_value={}):

        result = tmdb_service.get_show_details(999999)
        assert result["info"] == {}
        assert result["episode_groups"]["results"] == []
        assert result["alternative_titles"]["results"] == []
        assert result["external_ids"] == {}


# ────────────────────────────────────────────────
# GET SEASON DETAILS TESTS
# ────────────────────────────────────────────────

def test_get_show_season_details_success(tmdb_service):
    mock_season = {
        "id": 123,
        "name": "Season 1",
        "episodes": [{"episode_number": 1, "name": "Episode 1"}]
    }
    with patch('tmdbsimple.TV_Seasons.info', return_value=mock_season):
        result = tmdb_service.get_show_season_details(123, 1)
        assert result["episodes"][0]["episode_number"] == 1

def test_get_show_season_details_http_error(tmdb_service):
    with patch('tmdbsimple.TV_Seasons.info', side_effect=requests.exceptions.HTTPError):
        result = tmdb_service.get_show_season_details(123, 1)
        assert result is None

def test_get_show_season_details_general_error(tmdb_service):
    with patch('tmdbsimple.TV_Seasons.info', side_effect=Exception("General error")):
        with pytest.raises(Exception, match="General error"):
            tmdb_service.get_show_season_details(123, 1)

def test_get_show_season_details_empty(tmdb_service):
    with patch('tmdbsimple.TV_Seasons.info', return_value={"episodes": []}):
        result = tmdb_service.get_show_season_details(123, 1)
        assert result["episodes"] == []


# ────────────────────────────────────────────────
# GET EPISODE DETAILS TESTS
# ────────────────────────────────────────────────

def test_get_show_episode_details_success(tmdb_service):
    mock_episode = {
        "episode_number": 1,
        "name": "Episode 1",
        "overview": "First episode"
    }
    with patch('tmdbsimple.TV_Episodes.info', return_value=mock_episode):
        result = tmdb_service.get_show_episode_details(123, 1, 1)
        assert result["episode_number"] == 1
        assert result["name"] == "Episode 1"

def test_get_show_episode_details_http_error(tmdb_service):
    with patch('tmdbsimple.TV_Episodes.info', side_effect=requests.exceptions.HTTPError):
        result = tmdb_service.get_show_episode_details(123, 1, 1)
        assert result is None

def test_get_show_episode_details_general_error(tmdb_service):
    with patch('tmdbsimple.TV_Episodes.info', side_effect=Exception("General error")):
        with pytest.raises(Exception, match="General error"):
            tmdb_service.get_show_episode_details(123, 1, 1)

def test_get_show_episode_details_returns_none(tmdb_service):
    with patch('tmdbsimple.TV_Episodes.info', return_value=None):
        result = tmdb_service.get_show_episode_details(123, 1, 1)
        assert result is None


# ────────────────────────────────────────────────
# GET EPISODE GROUP DETAILS TESTS
# ────────────────────────────────────────────────

def test_get_episode_group_details_success(tmdb_service):
    mock_group = {
        "id": "abc",
        "groups": [],
        "type": 6
    }
    with patch('tmdbsimple.TV_Episode_Groups.info', return_value=mock_group):
        result = tmdb_service.get_episode_group_details("abc")
        assert result["id"] == "abc"
        assert result["type"] == 6

def test_get_episode_group_details_http_error(tmdb_service):
    with patch('tmdbsimple.TV_Episode_Groups.info', side_effect=requests.exceptions.HTTPError):
        result = tmdb_service.get_episode_group_details("abc")
        assert result is None

def test_get_episode_group_details_general_error(tmdb_service):
    with patch('tmdbsimple.TV_Episode_Groups.info', side_effect=Exception("General error")):
        with pytest.raises(Exception, match="General error"):
            tmdb_service.get_episode_group_details("abc")
