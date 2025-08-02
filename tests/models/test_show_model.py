import pytest
from models.show import Show
import datetime
import json
@pytest.fixture
def example_tmdb_details():
    return {
        "info": {
            "id": 123,
            "name": "Mock Show",
            "first_air_date": "2020-01-01",
            "last_air_date": "2020-12-31",
            "overview": "This is a mock show for testing.",
            "number_of_seasons": 2,
            "number_of_episodes": 10,
            "status": "Ended"
        },
        "episode_groups": {
            "results": [
                {"id": "group1", "type": 6, "name": "Production Order"},
                {"id": "group2", "type": 1, "name": "Original Air Date"}
            ]
        },
        "alternative_titles": {
            "results": [
                {"iso_3166_1": "US", "title": "Mock Show US"},
                {"iso_3166_1": "JP", "title": "モックショー"}
            ]
        },
        "external_ids": {
            "imdb_id": "tt1234567"
        }
    }

def test_from_tmdb_basic(example_tmdb_details):
    show = Show.from_tmdb(
        show_details=example_tmdb_details,
        sys_name="Mock_Show",
        sys_path="/test/path/Mock_Show"
    )

    assert show.tmdb_id == 123
    assert show.sys_name == "Mock_Show"
    assert show.sys_path == "/test/path/Mock_Show"
    assert show.tmdb_name == "Mock Show"
    # The aliases now include Mock Show, Mock Show US, モックショー, and Mock_Show (sys_name)
    assert "Mock Show" in show.tmdb_aliases
    assert "Mock Show US" in show.tmdb_aliases
    assert "モックショー" in show.tmdb_aliases
    assert "Mock_Show" in show.tmdb_aliases
    assert show.tmdb_first_aired == datetime.datetime(2020, 1, 1)
    assert show.tmdb_last_aired == datetime.datetime(2020, 12, 31)
    assert show.tmdb_season_count == 2
    assert show.tmdb_episode_count == 10
    assert show.tmdb_status == "Ended"
    # Recreate the external_ids dict from the json string
    external_ids = json.loads(show.tmdb_external_ids)
    assert external_ids["imdb_id"] == "tt1234567"

def test_to_db_tuple_matches(example_tmdb_details):
    show = Show.from_tmdb(
        show_details=example_tmdb_details,
        sys_name="Mock_Show",
        sys_path="/test/path/Mock_Show"
    )
    db_tuple = show.to_db_tuple()

    assert db_tuple[0] == "Mock_Show"
    assert db_tuple[1] == "/test/path/Mock_Show"
    assert db_tuple[2] == "Mock Show"
    # Check that the aliases contain all expected values
    aliases = db_tuple[3]
    assert "Mock Show" in aliases
    assert "Mock Show US" in aliases
    assert "モックショー" in aliases
    assert "Mock_Show" in aliases
    assert db_tuple[4] == 123
    assert isinstance(db_tuple[14], dict) or isinstance(db_tuple[14], str)  # tmdb_external_ids

# Edge cases
def test_show_from_tmdb_missing_optional_fields():
    minimal = {
        "info": {
            "id": 999,
            "name": "Incomplete Show",
            "first_air_date": None,
            "last_air_date": None,
            "overview": None,
            "number_of_seasons": None,
            "number_of_episodes": None,
            "status": None
        },
        "episode_groups": {"results": []},
        "alternative_titles": {"results": []},
        "external_ids": {}
    }
    show = Show.from_tmdb(minimal, sys_name="incomplete", sys_path="/mock/path")
    assert show.tmdb_name == "Incomplete Show"
    assert show.tmdb_first_aired is None
    # The episode_groups will be a JSON string representation of an empty list
    assert show.tmdb_episode_groups == "[]"
    # Aliases will include the show name and sys_name
    assert "Incomplete Show" in show.tmdb_aliases
    assert "incomplete" in show.tmdb_aliases

def test_show_to_db_tuple_valid_structure():
    data = {
        "info": {
            "id": 1001,
            "name": "Edge Show",
            "first_air_date": "2023-01-01",
            "last_air_date": "2023-02-01",
            "overview": "Edge case overview.",
            "number_of_seasons": 1,
            "number_of_episodes": 1,
            "status": "Airing"
        },
        "episode_groups": {"results": []},
        "alternative_titles": {"results": []},
        "external_ids": {}
    }
    show = Show.from_tmdb(data, sys_name="edge_show", sys_path="/path/edge_show")
    tpl = show.to_db_tuple()
    assert isinstance(tpl, tuple)
    assert len(tpl) == 16