import pytest
from unittest.mock import MagicMock
from utils.episode_updater import refresh_episodes_for_show
from models.show import Show

@pytest.fixture
def mock_show():
    return Show(
        sys_name="Test Show",
        sys_path="/fake/path",
        tmdb_name="Test Show",
        tmdb_aliases=None,
        tmdb_id=12345,
        tmdb_first_aired=None,
        tmdb_last_aired=None,
        tmdb_year=None,
        tmdb_overview=None,
        tmdb_season_count=None,
        tmdb_episode_count=None,
        tmdb_episode_groups=None,
        tmdb_status=None,
        tmdb_external_ids=None,
        tmdb_episodes_fetched_at=None,
        fetched_at=None
    )

def test_refresh_episodes_success(monkeypatch, mock_show):
    db = MagicMock()
    tmdb = MagicMock()
    # Simulate TMDB returning valid details
    tmdb.get_show_details.return_value = {
        "info": {"number_of_seasons": 1},
        "episode_groups": {"results": []}
    }
    # Patch Episode.parse_from_tmdb to return 3 fake episodes
    monkeypatch.setattr(
        "models.episode.Episode.parse_from_tmdb",
        lambda tmdb_id, tmdb_service, episode_groups, season_count: [1, 2, 3]
    )
    count = refresh_episodes_for_show(db, tmdb, mock_show, dry_run=False)
    assert count == 3
    db.add_episodes.assert_called_once_with([1, 2, 3])

def test_refresh_episodes_tmdb_failure(mock_show):
    db = MagicMock()
    tmdb = MagicMock()
    # Simulate TMDB returning None
    tmdb.get_show_details.return_value = None
    count = refresh_episodes_for_show(db, tmdb, mock_show, dry_run=False)
    assert count == 0
    db.add_episodes.assert_not_called()

def test_refresh_episodes_dry_run(monkeypatch, mock_show):
    db = MagicMock()
    tmdb = MagicMock()
    tmdb.get_show_details.return_value = {
        "info": {"number_of_seasons": 2},
        "episode_groups": {"results": []}
    }
    monkeypatch.setattr(
        "models.episode.Episode.parse_from_tmdb",
        lambda tmdb_id, tmdb_service, episode_groups, season_count: ["ep1", "ep2"]
    )
    count = refresh_episodes_for_show(db, tmdb, mock_show, dry_run=True)
    assert count == 2
    db.add_episodes.assert_not_called() 