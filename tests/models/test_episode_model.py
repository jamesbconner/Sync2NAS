import pytest
import datetime
from models.episode import Episode


def test_episode_to_db_tuple():
    episode = Episode(
        tmdb_id=123,
        season=1,
        episode=1,
        abs_episode=1,
        episode_type="standard",
        episode_id=456,
        air_date=datetime.datetime(2023, 1, 1),
        fetched_at=datetime.datetime(2023, 1, 2),
        name="Pilot",
        overview="First episode."
    )

    result = episode.to_db_tuple()

    assert result == (
        123, 1, 1, 1, "standard", 456,
        datetime.datetime(2023, 1, 1),
        datetime.datetime(2023, 1, 2),
        "Pilot", "First episode."
    )


def test_parse_date_valid():
    date_str = "2023-01-01"
    parsed = Episode._parse_date(date_str)
    assert isinstance(parsed, datetime.datetime)
    assert parsed.isoformat() == "2023-01-01T00:00:00"


def test_parse_date_none():
    assert Episode._parse_date(None) is None


def test_parse_date_invalid():
    assert Episode._parse_date("not-a-date") is None


def test_parse_from_tmdb_fallback_to_seasons(mock_tmdb_service):
    episodes = Episode.parse_from_tmdb(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups=[],  # No production groups to trigger fallback
        season_count=1
    )

    assert isinstance(episodes, list)
    assert len(episodes) == 3
    assert episodes[0].episode == 1
    assert episodes[1].episode == 2
    assert episodes[2].episode == 3


def test_parse_from_tmdb_with_bad_season(mock_tmdb_service):
    # Simulate an empty or invalid season response
    mock_tmdb_service.get_show_season_details.return_value = {}
    episodes = Episode.parse_from_tmdb(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups=[],
        season_count=1
    )
    assert episodes == []

# Edge Cases
def test_episode_negative_numbers():
    ep = Episode(
        tmdb_id=-1,
        season=-1,
        episode=-1,
        abs_episode=-1,
        episode_type="standard",
        episode_id=-100,
        air_date=None,
        fetched_at=datetime.datetime.now(),
        name="Negative",
        overview="Negative test"
    )
    assert ep.tmdb_id == -1
    assert ep.season == -1

def test_episode_missing_fields():
    ep = Episode(
        tmdb_id=0,
        season=1,
        episode=1,
        abs_episode=1,
        episode_type="",
        episode_id=0,
        air_date=None,
        fetched_at=datetime.datetime.now(),
        name="",
        overview=""
    )
    assert ep.name == ""
    assert ep.overview == ""

def test_episode_to_db_tuple_structure():
    ep = Episode(
        tmdb_id=1,
        season=1,
        episode=1,
        abs_episode=1,
        episode_type="standard",
        episode_id=100,
        air_date=None,
        fetched_at=datetime.datetime.now(),
        name="Test Ep",
        overview="Testing"
    )
    tpl = ep.to_db_tuple()
    assert isinstance(tpl, tuple)
    assert len(tpl) == 10