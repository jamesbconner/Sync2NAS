import pytest
import datetime
from pathlib import Path
from models.episode import Episode
from models.show import Show
from services.db_service import DBService
from utils.show_adder import add_show_interactively

@pytest.fixture
def mock_details():
    return {
        "info": {
            "id": 123,
            "name": "Mock Show",
            "first_air_date": "2020-01-01",
            "number_of_seasons": 1,
            "number_of_episodes": 3,
            "overview": "Test Overview"
        },
        "episode_groups": {"results": []},
        "alternative_titles": {"results": []},
        "external_ids": {}
    }

@pytest.fixture
def mock_tmdb_service(mock_details):
    class MockTMDB:
        def search_show(self, name):
            return {"results": [{"id": 123, "name": name, "first_air_date": "2020-01-01"}]}

        def get_show_details(self, tmdb_id):
            return mock_details

        def get_show_season_details(self, tmdb_id, season_number):
            return {
                "id": season_number,
                "air_date": "2020-01-01",
                "season_number": season_number,
                "episodes": [
                    {
                        "episode_number": 1,
                        "id": 1001,
                        "air_date": "2020-01-01",
                        "name": "Episode 1",
                        "overview": "Overview 1",
                    },
                    {
                        "episode_number": 2,
                        "id": 1002,
                        "air_date": "2020-01-08",
                        "name": "Episode 2",
                        "overview": "Overview 2",
                    },
                    {
                        "episode_number": 3,
                        "id": 1003,
                        "air_date": "2020-01-15",
                        "name": "Episode 3",
                        "overview": "Overview 3",
                    },
                ],
            }

    return MockTMDB()


def test_add_show_interactively(tmp_path, mock_tmdb_service):
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    db = DBService(str(db_path))
    db.initialize()

    result = add_show_interactively(
        show_name="Mock Show",
        tmdb_id=None,
        db=db,
        tmdb=mock_tmdb_service,
        anime_tv_path=str(anime_tv_path),
        dry_run=False
    )

    shows = db.get_all_shows()
    episodes = db.get_episodes_by_show_name("Mock Show")

    assert result["tmdb_name"] == "Mock Show"
    assert result["episode_count"] == 3
    assert shows[0]["sys_name"] == "Mock Show"
    assert len(episodes) == 3

def test_add_show_interactively_dry_run(tmp_path, mock_tmdb_service):
    db_path = tmp_path / "test.db"
    anime_tv_path = tmp_path / "anime_tv_path"
    anime_tv_path.mkdir()
    db = DBService(str(db_path))
    db.initialize()

    result = add_show_interactively(
        show_name="Mock Show",
        tmdb_id=None,
        db=db,
        tmdb=mock_tmdb_service,
        anime_tv_path=str(anime_tv_path),
        dry_run=True
    )

    assert result["tmdb_name"] == "Mock Show"
    assert result["episode_count"] == 3
    assert db.get_all_shows() == []
