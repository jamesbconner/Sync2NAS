import pytest
from models.show import Show
from models.episode import Episode
import datetime

def test_add_show_and_query(db_service):
    show = Show(
        sys_name="TestShow",
        sys_path="/fake/path/TestShow",
        tmdb_name="Test Show",
        tmdb_aliases="",
        tmdb_id=1,
        tmdb_first_aired=datetime.datetime.now(),
        tmdb_last_aired=datetime.datetime.now(),
        tmdb_year=2020,
        tmdb_overview="Overview",
        tmdb_season_count=1,
        tmdb_episode_count=3,
        tmdb_episode_groups="[]",
        tmdb_episodes_fetched_at=datetime.datetime.now(),
        tmdb_status="Ended",
        tmdb_external_ids="{}",
        fetched_at=datetime.datetime.now()
    )
    db_service.add_show(show)
    assert db_service.show_exists("TestShow")

def test_add_episodes_and_query(db_service):
    episode = Episode(
        tmdb_id=1,
        season=1,
        episode=1,
        abs_episode=1,
        episode_type="standard",
        episode_id=101,
        air_date=datetime.datetime.now(),
        fetched_at=datetime.datetime.now(),
        name="Ep 1",
        overview="Ep overview"
    )
    db_service.add_episode(episode)
    assert db_service.episodes_exist(1)

def test_delete_show_and_episodes(db_service):
    db_service.delete_show_and_episodes(1)
    assert not db_service.episodes_exist(1)
    
# Edge cases
def test_show_exists_alias_match(db_service):
    class FakeShow:
        tmdb_name = "The Real Show"
        def to_db_tuple(self):
            return (
                "Test Show", "/fake/path", "The Real Show", "alias1, alias2", 101,
                None, None, None, None, 1, 10, None, None, "Ended", None, None)
    db_service.add_show(FakeShow())
    assert db_service.show_exists("alias2")

def test_episodes_exist_false(db_service):
    assert not db_service.episodes_exist(9999)

def test_delete_nonexistent_show_and_episodes(db_service):
    db_service.delete_show_and_episodes(tmdb_id=404)  # Should not raise

def test_get_episodes_by_nonexistent_show_name(db_service):
    episodes = db_service.get_episodes_by_show_name("DoesNotExist")
    assert episodes == []