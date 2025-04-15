import os
import shutil
import pytest
import datetime
from unittest.mock import Mock
from utils.file_routing import file_routing
from services.db_service import DBService

@pytest.fixture
def setup_test_environment(tmp_path, mocker):
    incoming = tmp_path / "incoming"
    incoming.mkdir()

    show_dir = tmp_path / "tv_shows" / "Bleach"
    show_dir.mkdir(parents=True)

    db = Mock(spec=DBService)

    # Create file simulating: Bleach.S02.E06.mkv
    file_path = incoming / "Bleach.S02.E06.mkv"
    file_path.write_text("dummy content")

    # Simulate DB show lookup
    db.get_show_by_name_or_alias.return_value = {
        "sys_name": "Bleach",
        "sys_path": str(show_dir),
        "tmdb_id": 123,
        "tmdb_name": "Bleach",
        "tmdb_aliases": "BLEACH 千年血战篇,BLEACH 千年血戦篇,BLEACH 千年血戦篇ー相剋譚ー",
        "tmdb_first_aired": None,
        "tmdb_last_aired": None,
        "tmdb_year": None,
        "tmdb_overview": "",
        "tmdb_season_count": 0,
        "tmdb_episode_count": 0,
        "tmdb_episode_groups": None,
        "tmdb_status": None,
        "tmdb_external_ids": None,
        "tmdb_episodes_fetched_at": None,
        "fetched_at": datetime.datetime(2025, 4, 10, 12, 0, 0)
    }

    # Simulate known episode return
    db.get_episode_by_absolute_number.return_value = {
        "season": 6,
        "episode": 15
    }

    return incoming, db, show_dir, file_path

def test_file_route_season_episode_parsing_and_move(setup_test_environment):
    incoming, db, show_dir, file_path = setup_test_environment

    

    result = file_routing(str(incoming), str(show_dir.parent), db)

    # Check that the file has been moved
    season_dir = show_dir / "Season 02"
    routed_file = season_dir / "Bleach.S02.E06.mkv"
    assert routed_file.exists()
    assert not file_path.exists()

    # Check metadata
    assert len(result) == 1
    routed = result[0]
    assert routed["show_name"] == "Bleach"
    assert routed["season"] == "02"
    assert routed["episode"] == "06"

def test_file_route_fallback_to_absolute_episode(tmp_path, mocker):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    file_path = incoming / "Bleach - 101.mkv"
    file_path.write_text("dummy content")

    show_dir = tmp_path / "tv_shows" / "Bleach"
    show_dir.mkdir(parents=True)

    db = Mock(spec=DBService)
    db.get_show_by_name_or_alias.return_value = {
        "sys_name": "Bleach",
        "sys_path": str(show_dir),
        "tmdb_id": 123,
        "tmdb_name": "Bleach",
        "tmdb_aliases": "BLEACH 千年血战篇,BLEACH 千年血戦篇,BLEACH 千年血戦篇ー相剋譚ー",
        "tmdb_first_aired": None,
        "tmdb_last_aired": None,
        "tmdb_year": None,
        "tmdb_overview": "",
        "tmdb_season_count": 0,
        "tmdb_episode_count": 0,
        "tmdb_episode_groups": None,
        "tmdb_status": None,
        "tmdb_external_ids": None,
        "tmdb_episodes_fetched_at": None,
        "fetched_at": datetime.datetime(2025, 4, 10, 12, 0, 0)
    }

    db.get_episode_by_absolute_number.return_value = {
        "season": 6,
        "episode": 101
    }

    result = file_routing(str(incoming), str(show_dir.parent), db)

    season_dir = show_dir / "Season 06"
    routed_file = season_dir / "Bleach - 101.mkv"
    assert routed_file.exists()

    assert len(result) == 1
    routed = result[0]
    assert routed["season"] == "06"
    assert routed["episode"] == "101"

def test_file_route_skips_unmatched_show(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "UnknownShow.S01E01.mkv").write_text("no match")

    db = Mock(spec=DBService)
    db.get_show_by_name_or_alias.return_value = None

    result = file_routing(str(incoming), None, db)
    assert result == []

def test_file_route_skips_unmatched_episode(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "Bleach - 9999.mkv").write_text("no match")

    show_dir = tmp_path / "tv_shows" / "Bleach"
    show_dir.mkdir(parents=True)

    db = Mock(spec=DBService)
    db.get_show_by_name_or_alias.return_value = {
        "sys_name": "Bleach",
        "sys_path": str(show_dir),
        "tmdb_id": 123,
        "tmdb_name": "Bleach",
        "tmdb_aliases": "BLEACH 千年血战篇,BLEACH 千年血戦篇,BLEACH 千年血戦篇ー相剋譚ー",
        "tmdb_first_aired": None,
        "tmdb_last_aired": None,
        "tmdb_year": None,
        "tmdb_overview": "",
        "tmdb_season_count": 0,
        "tmdb_episode_count": 0,
        "tmdb_episode_groups": None,
        "tmdb_status": None,
        "tmdb_external_ids": None,
        "tmdb_episodes_fetched_at": None,
        "fetched_at": datetime.datetime(2025, 4, 10, 12, 0, 0)
    }

    db.get_episode_by_absolute_number.return_value = None

    result = file_routing(str(incoming), str(show_dir.parent), db)
    assert result == []
