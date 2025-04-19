import os
import shutil
import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock
from utils.file_routing import parse_filename, file_routing
from services.db_service import DBService
from models.show import Show

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

def test_parse_filename_method1():
    """Test parsing filename with format: [Group] Show Name (Year) - Episode"""
    filename = "[Group] Show Name (2020) - 1"
    show_name, episode, season, year = parse_filename(filename)
    assert show_name == "Show Name"
    assert episode == "1"
    assert season is None
    assert year == "2020"

def test_parse_filename_method2():
    """Test parsing filename with format: [Group] Show Name S01 - 01"""
    filename = "[Group] Show Name S1 - 01"
    show_name, episode, season, year = parse_filename(filename)
    assert show_name == "Show Name"
    assert episode == "01"
    assert season == "1"
    assert year is None

def test_parse_filename_method3():
    """Test parsing filename with format: Show.Name.2000.S01E01"""
    filename = "Show.Name.2000.S01E01"
    show_name, episode, season, year = parse_filename(filename)
    assert show_name == "Show Name"
    assert episode == "01"
    assert season == "01"
    assert year == "2000"

def test_parse_filename_method4():
    """Test parsing filename with format: Show Name - 101 [abc123]"""
    filename = "Show Name - 101 [abc123]"
    show_name, episode, season, year = parse_filename(filename)
    assert show_name == "Show Name"
    assert episode == "101"
    assert season is None
    assert year is None

def test_parse_filename_unrecognized_format():
    """Test parsing filename with unrecognized format"""
    filename = "random.file.name"
    show_name, episode, season, year = parse_filename(filename)
    assert show_name is None
    assert episode is None
    assert season is None
    assert year is None

def test_file_routing_dry_run(tmp_path):
    """Test file routing in dry run mode"""
    incoming_path = tmp_path / "incoming"
    anime_tv_path = tmp_path / "anime_tv"
    incoming_path.mkdir()
    anime_tv_path.mkdir()

    # Create a test file
    test_file = incoming_path / "[Group] Show Name (2020) - 1.mkv"
    test_file.write_text("test content")

    # Mock DB service
    mock_db = MagicMock(spec=DBService)
    
    # Mock show lookup with complete show record
    mock_db.get_show_by_name_or_alias.return_value = {
        "sys_name": "Show Name",
        "sys_path": str(anime_tv_path / "Show Name"),
        "tmdb_id": 123,
        "tmdb_name": "Show Name",
        "tmdb_aliases": None,
        "tmdb_first_aired": None,
        "tmdb_last_aired": None,
        "tmdb_year": None,
        "tmdb_overview": None,
        "tmdb_season_count": 0,
        "tmdb_episode_count": 0,
        "tmdb_episode_groups": None,
        "tmdb_status": None,
        "tmdb_external_ids": None,
        "tmdb_episodes_fetched_at": None,
        "fetched_at": None
    }
    mock_db.get_episode_by_absolute_number.return_value = {"season": 1, "episode": 1}

    # Run file routing in dry run mode
    result = file_routing(str(incoming_path), str(anime_tv_path), mock_db, dry_run=True)

    # Verify results
    assert len(result) == 1
    assert result[0]["original_path"] == str(test_file)
    assert result[0]["routed_path"] == str(anime_tv_path / "Show Name" / "Season 01" / test_file.name)
    assert result[0]["show_name"] == "Show Name"

    # Verify file wasn't actually moved
    assert test_file.exists()
    assert not (anime_tv_path / "Show Name" / "Season 01" / test_file.name).exists()

def test_file_routing_actual_move(tmp_path):
    """Test file routing with actual file movement"""
    incoming_path = tmp_path / "incoming"
    anime_tv_path = tmp_path / "anime_tv"
    incoming_path.mkdir()
    anime_tv_path.mkdir()

    # Create a test file
    test_file = incoming_path / "[Group] Show Name (2020) - 1.mkv"
    test_file.write_text("test content")

    # Mock DB service
    mock_db = MagicMock(spec=DBService)
    
    # Mock show lookup with complete show record
    mock_db.get_show_by_name_or_alias.return_value = {
        "sys_name": "Show Name",
        "sys_path": str(anime_tv_path / "Show Name"),
        "tmdb_id": 123,
        "tmdb_name": "Show Name",
        "tmdb_aliases": None,
        "tmdb_first_aired": None,
        "tmdb_last_aired": None,
        "tmdb_year": None,
        "tmdb_overview": None,
        "tmdb_season_count": 0,
        "tmdb_episode_count": 0,
        "tmdb_episode_groups": None,
        "tmdb_status": None,
        "tmdb_external_ids": None,
        "tmdb_episodes_fetched_at": None,
        "fetched_at": None
    }
    mock_db.get_episode_by_absolute_number.return_value = {"season": 1, "episode": 1}

    # Run file routing
    result = file_routing(str(incoming_path), str(anime_tv_path), mock_db, dry_run=False)

    # Verify results
    assert len(result) == 1
    assert result[0]["original_path"] == str(test_file)
    assert result[0]["routed_path"] == str(anime_tv_path / "Show Name" / "Season 01" / test_file.name)
    assert result[0]["show_name"] == "Show Name"

    # Verify file was actually moved
    assert not test_file.exists()
    assert (anime_tv_path / "Show Name" / "Season 01" / test_file.name).exists()

def test_file_routing_no_show_match(tmp_path):
    """Test file routing when no matching show is found"""
    incoming_path = tmp_path / "incoming"
    anime_tv_path = tmp_path / "anime_tv"
    incoming_path.mkdir()
    anime_tv_path.mkdir()

    # Create a test file
    test_file = incoming_path / "[Group] Show Name (2020) - 1.mkv"
    test_file.write_text("test content")

    # Mock DB service with no show match
    mock_db = MagicMock(spec=DBService)
    mock_db.get_show_by_name_or_alias.return_value = None

    # Run file routing
    result = file_routing(str(incoming_path), str(anime_tv_path), mock_db, dry_run=False)

    # Verify no files were routed
    assert len(result) == 0
    assert test_file.exists()  # File should still be in incoming directory

def test_file_routing_no_episode_match(tmp_path):
    """Test file routing when no matching episode is found"""
    incoming_path = tmp_path / "incoming"
    anime_tv_path = tmp_path / "anime_tv"
    incoming_path.mkdir()
    anime_tv_path.mkdir()

    # Create a test file
    test_file = incoming_path / "Show Name - 101.mkv"
    test_file.write_text("test content")

    # Mock DB service
    mock_db = MagicMock(spec=DBService)
    
    # Mock show lookup with complete show record
    mock_db.get_show_by_name_or_alias.return_value = {
        "sys_name": "Show Name",
        "sys_path": str(anime_tv_path / "Show Name"),
        "tmdb_id": 123,
        "tmdb_name": "Show Name",
        "tmdb_aliases": None,
        "tmdb_first_aired": None,
        "tmdb_last_aired": None,
        "tmdb_year": None,
        "tmdb_overview": None,
        "tmdb_season_count": 0,
        "tmdb_episode_count": 0,
        "tmdb_episode_groups": None,
        "tmdb_status": None,
        "tmdb_external_ids": None,
        "tmdb_episodes_fetched_at": None,
        "fetched_at": None
    }
    mock_db.get_episode_by_absolute_number.return_value = None

    # Run file routing
    result = file_routing(str(incoming_path), str(anime_tv_path), mock_db, dry_run=False)

    # Verify no files were routed
    assert len(result) == 0
    assert test_file.exists()  # File should still be in incoming directory
