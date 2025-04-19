import pytest
from unittest.mock import patch, MagicMock
import requests
from services.tmdb_service import TMDBService

@pytest.fixture
def mock_tmdb_service():
    service = TMDBService("dummy_api_key")
    return service

def test_search_show(mock_tmdb_service):
    mock_response = {
        "results": [
            {
                "name": "Mock Show",
                "id": 123,
                "overview": "A mock show for testing",
                "first_air_date": "2020-01-01",
                "poster_path": "/mock.jpg"
            }
        ]
    }
    with patch('tmdbsimple.Search.tv', return_value=mock_response):
        results = mock_tmdb_service.search_show("Mock Show")
        assert results is not None
        assert "results" in results
        assert results["results"][0]["name"] == "Mock Show"

def test_search_show_http_error(mock_tmdb_service):
    with patch('tmdbsimple.Search.tv', side_effect=requests.exceptions.HTTPError()):
        result = mock_tmdb_service.search_show("Error Show")
        assert result is None

def test_search_show_general_error(mock_tmdb_service):
    with patch('tmdbsimple.Search.tv', side_effect=Exception("General error")):
        result = mock_tmdb_service.search_show("Error Show")
        assert result is None

def test_get_show_details(mock_tmdb_service):
    mock_info = {
        "name": "Mock Show",
        "id": 123,
        "overview": "A mock show for testing",
        "first_air_date": "2020-01-01"
    }
    mock_episode_groups = {"results": []}
    mock_alternative_titles = {"results": []}
    mock_external_ids = {"imdb_id": "tt1234567"}
    
    with patch('tmdbsimple.TV.info', return_value=mock_info), \
         patch('tmdbsimple.TV.episode_groups', return_value=mock_episode_groups), \
         patch('tmdbsimple.TV.alternative_titles', return_value=mock_alternative_titles), \
         patch('tmdbsimple.TV.external_ids', return_value=mock_external_ids):
        details = mock_tmdb_service.get_show_details(123)
        assert "info" in details
        assert details["info"]["name"] == "Mock Show"
        assert details["episode_groups"]["results"] == []
        assert details["alternative_titles"]["results"] == []
        assert details["external_ids"]["imdb_id"] == "tt1234567"

def test_get_show_details_http_error(mock_tmdb_service):
    with patch('tmdbsimple.TV.info', side_effect=requests.exceptions.HTTPError()):
        result = mock_tmdb_service.get_show_details(123)
        assert result is None

def test_get_show_details_general_error(mock_tmdb_service):
    with patch('tmdbsimple.TV.info', side_effect=Exception("General error")):
        result = mock_tmdb_service.get_show_details(123)
        assert result is None

def test_get_show_season_details(mock_tmdb_service):
    mock_season = {
        "id": 123,
        "name": "Season 1",
        "episodes": [
            {
                "episode_number": 1,
                "name": "Episode 1",
                "overview": "First episode"
            }
        ]
    }
    with patch('tmdbsimple.TV_Seasons.info', return_value=mock_season):
        season = mock_tmdb_service.get_show_season_details(123, 1)
        assert "episodes" in season
        assert season["episodes"][0]["episode_number"] == 1

def test_get_show_season_details_http_error(mock_tmdb_service):
    with patch('tmdbsimple.TV_Seasons.info', side_effect=requests.exceptions.HTTPError()):
        result = mock_tmdb_service.get_show_season_details(123, 1)
        assert result is None

def test_get_show_season_details_general_error(mock_tmdb_service):
    with patch('tmdbsimple.TV_Seasons.info', side_effect=Exception("General error")):
        result = mock_tmdb_service.get_show_season_details(123, 1)
        assert result is None

def test_get_show_episode_details(mock_tmdb_service):
    mock_episode = {
        "episode_number": 1,
        "name": "Episode 1",
        "overview": "First episode",
        "air_date": "2020-01-01"
    }
    with patch('tmdbsimple.TV_Episodes.info', return_value=mock_episode):
        episode = mock_tmdb_service.get_show_episode_details(123, 1, 1)
        assert episode["episode_number"] == 1
        assert episode["name"] == "Episode 1"

def test_get_show_episode_details_http_error(mock_tmdb_service):
    with patch('tmdbsimple.TV_Episodes.info', side_effect=requests.exceptions.HTTPError()):
        result = mock_tmdb_service.get_show_episode_details(123, 1, 1)
        assert result is None

def test_get_show_episode_details_general_error(mock_tmdb_service):
    with patch('tmdbsimple.TV_Episodes.info', side_effect=Exception("General error")):
        result = mock_tmdb_service.get_show_episode_details(123, 1, 1)
        assert result is None

def test_get_episode_group_details(mock_tmdb_service):
    mock_group = {
        "id": "abc",
        "groups": [],
        "type": 6
    }
    with patch('tmdbsimple.TV_Episode_Groups.info', return_value=mock_group):
        group = mock_tmdb_service.get_episode_group_details("abc")
        assert group["id"] == "abc"
        assert group["type"] == 6

def test_get_episode_group_details_http_error(mock_tmdb_service):
    with patch('tmdbsimple.TV_Episode_Groups.info', side_effect=requests.exceptions.HTTPError()):
        result = mock_tmdb_service.get_episode_group_details("abc")
        assert result is None

def test_get_episode_group_details_general_error(mock_tmdb_service):
    with patch('tmdbsimple.TV_Episode_Groups.info', side_effect=Exception("General error")):
        result = mock_tmdb_service.get_episode_group_details("abc")
        assert result is None

# Edge cases
def test_search_show_returns_empty_results(mock_tmdb_service):
    with patch('tmdbsimple.Search.tv', return_value={"results": []}):
        result = mock_tmdb_service.search_show("NoSuchShow")
        assert isinstance(result, dict)
        assert result["results"] == []

def test_get_show_details_missing_fields(mock_tmdb_service):
    with patch('tmdbsimple.TV.info', return_value={}), \
         patch('tmdbsimple.TV.episode_groups', return_value={"results": []}), \
         patch('tmdbsimple.TV.alternative_titles', return_value={"results": []}), \
         patch('tmdbsimple.TV.external_ids', return_value={}):
        result = mock_tmdb_service.get_show_details(999999)
        assert result["info"] == {}
        assert result["episode_groups"]["results"] == []
        assert result["alternative_titles"]["results"] == []
        assert result["external_ids"] == {}

def test_get_show_season_details_empty(mock_tmdb_service):
    with patch('tmdbsimple.TV_Seasons.info', return_value={"episodes": []}):
        result = mock_tmdb_service.get_show_season_details(123, 1)
        assert result["episodes"] == []

def test_get_show_episode_details_returns_none(mock_tmdb_service):
    with patch('tmdbsimple.TV_Episodes.info', return_value=None):
        result = mock_tmdb_service.get_show_episode_details(123, 1, 1)
        assert result is None