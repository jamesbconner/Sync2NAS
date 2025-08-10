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
    """Test that Pydantic validation rejects negative numbers."""
    import pytest
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError) as exc_info:
        Episode(
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
    
    # Check that we get validation errors for the expected fields
    errors = exc_info.value.errors()
    error_fields = [error['loc'][0] for error in errors]
    assert 'tmdb_id' in error_fields
    assert 'season' in error_fields
    assert 'episode' in error_fields
    assert 'abs_episode' in error_fields
    assert 'episode_id' in error_fields

def test_episode_missing_fields():
    """Test that Pydantic validation rejects invalid field values."""
    import pytest
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError) as exc_info:
        Episode(
            tmdb_id=0,  # Should be > 0
            season=1,
            episode=1,
            abs_episode=1,
            episode_type="",
            episode_id=0,  # Should be > 0
            air_date=None,
            fetched_at=datetime.datetime.now(),
            name="",
            overview=""
        )
    
    # Check that we get validation errors for the expected fields
    errors = exc_info.value.errors()
    error_fields = [error['loc'][0] for error in errors]
    # TMDB id of 0 is acceptable; episode_id must still be > 0
    assert 'episode_id' in error_fields

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

def test_from_production_groups_success(mock_tmdb_service):
    # Mock the episode group details response
    mock_tmdb_service.get_episode_group_details.return_value = {
        "groups": [
            {
                "order": 1,
                "episodes": [
                    {
                        "order": 0,
                        "episode_number": 1,
                        "episode_type": "standard",
                        "id": 456,
                        "air_date": "2023-01-01",
                        "name": "Pilot",
                        "overview": "First episode"
                    }
                ]
            }
        ]
    }

    episodes = Episode._from_production_groups(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups_meta=[{"type": 6, "id": "group1"}]
    )

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.tmdb_id == 123
    assert episode.season == 1
    assert episode.episode == 1
    assert episode.abs_episode == 1
    assert episode.episode_type == "standard"
    assert episode.episode_id == 456
    assert episode.air_date.isoformat() == "2023-01-01T00:00:00"
    assert episode.name == "Pilot"
    assert episode.overview == "First episode"

def test_from_production_groups_no_groups():
    with pytest.raises(ValueError, match="No production episode groups found"):
        Episode._from_production_groups(
            tmdb_id=123,
            tmdb_service=None,
            episode_groups_meta=[{"type": 5}]  # Not a production group
        )

def test_from_production_groups_empty_group_details(mock_tmdb_service):
    mock_tmdb_service.get_episode_group_details.return_value = None

    episodes = Episode._from_production_groups(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups_meta=[{"type": 6, "id": "group1"}]
    )

    assert episodes == []

def test_from_production_groups_invalid_episode_data(mock_tmdb_service):
    mock_tmdb_service.get_episode_group_details.return_value = {
        "groups": [
            {
                "order": 1,
                "episodes": [
                    {
                        "order": "invalid",  # Invalid order type
                        "episode_number": "invalid",  # Invalid episode number
                        "episode_type": "standard",
                        "id": 456,
                        "air_date": "not-a-date",  # Invalid date
                        "name": "Pilot",
                        "overview": "First episode"
                    }
                ]
            }
        ]
    }

    episodes = Episode._from_production_groups(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups_meta=[{"type": 6, "id": "group1"}]
    )

    assert episodes == []

def test_from_production_groups_missing_episode_number(mock_tmdb_service):
    """Test that episodes with missing episode_number are handled correctly."""
    mock_tmdb_service.get_episode_group_details.return_value = {
        "groups": [
            {
                "order": 1,
                "episodes": [
                    {
                        "order": 0,
                        # Missing episode_number - should default to 0
                        "episode_type": "standard",
                        "id": 456,
                        "air_date": "2023-01-01",
                        "name": "Pilot",
                        "overview": "First episode"
                    },
                    {
                        "order": 1,
                        "episode_number": None,  # Explicitly None
                        "episode_type": "standard",
                        "id": 457,
                        "air_date": "2023-01-08",
                        "name": "Second Episode",
                        "overview": "Second episode"
                    }
                ]
            }
        ]
    }

    episodes = Episode._from_production_groups(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups_meta=[{"type": 6, "id": "group1"}]
    )

    assert len(episodes) == 2
    # First episode should have abs_episode=0 (default)
    assert episodes[0].abs_episode == 0
    # Second episode should have abs_episode=0 (None defaults to 0)
    assert episodes[1].abs_episode == 0

def test_parse_from_tmdb_exception_handling(mock_tmdb_service):
    # Make both production groups and seasons fail
    mock_tmdb_service.get_episode_group_details.side_effect = Exception("Test error")
    mock_tmdb_service.get_show_season_details.side_effect = Exception("Test error")

    episodes = Episode.parse_from_tmdb(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups=[{"type": 6, "id": "group1"}],
        season_count=1
    )

    assert episodes == []

def test_parse_from_tmdb_with_production_groups(mock_tmdb_service):
    # Mock the episode group details response
    mock_tmdb_service.get_episode_group_details.return_value = {
        "groups": [
            {
                "order": 1,
                "episodes": [
                    {
                        "order": 0,
                        "episode_number": 1,
                        "episode_type": "standard",
                        "id": 456,
                        "air_date": "2023-01-01",
                        "name": "Pilot",
                        "overview": "First episode"
                    }
                ]
            }
        ]
    }

    episodes = Episode.parse_from_tmdb(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups=[{"type": 6, "id": "group1"}],
        season_count=1
    )

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.tmdb_id == 123
    assert episode.season == 1
    assert episode.episode == 1
    assert episode.abs_episode == 1
    assert episode.episode_type == "standard"
    assert episode.episode_id == 456
    assert episode.air_date.isoformat() == "2023-01-01T00:00:00"
    assert episode.name == "Pilot"
    assert episode.overview == "First episode"

def test_parse_from_tmdb_with_seasons(mock_tmdb_service):
    # Mock the season details response
    mock_tmdb_service.get_show_season_details.return_value = {
        "episodes": [
            {
                "episode_number": 1,
                "name": "Season Episode 1",
                "overview": "First episode of season",
                "air_date": "2023-01-01",
                "id": 456
            }
        ]
    }

    episodes = Episode.parse_from_tmdb(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups=[],  # No production groups to trigger fallback
        season_count=1
    )

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.tmdb_id == 123
    assert episode.season == 1
    assert episode.episode == 1
    assert episode.abs_episode == 1
    assert episode.episode_type == "standard"
    assert episode.episode_id == 456
    assert episode.air_date.isoformat() == "2023-01-01T00:00:00"
    assert episode.name == "Season Episode 1"
    assert episode.overview == "First episode of season"

def test_parse_from_tmdb_with_invalid_json(mock_tmdb_service):
    # Test handling of invalid JSON in episode_groups
    episodes = Episode.parse_from_tmdb(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups="invalid_json",  # Invalid JSON string
        season_count=1
    )

    # Should fall back to seasons
    assert len(episodes) > 0

def test_parse_from_tmdb_with_empty_season_count(mock_tmdb_service):
    # Test handling of None or 0 season_count
    episodes = Episode.parse_from_tmdb(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups=[],
        season_count=0
    )

    assert episodes == []

def test_parse_from_tmdb_with_missing_episode_data(mock_tmdb_service):
    # Mock season details with missing required fields
    mock_tmdb_service.get_show_season_details.return_value = {
        "episodes": [
            {
                # Missing episode_number
                "name": "Invalid Episode",
                "overview": "This episode is missing required fields"
            }
        ]
    }

    episodes = Episode.parse_from_tmdb(
        tmdb_id=123,
        tmdb_service=mock_tmdb_service,
        episode_groups=[],
        season_count=1
    )

    assert episodes == []