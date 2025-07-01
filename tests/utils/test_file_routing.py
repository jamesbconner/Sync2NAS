import os
import shutil
import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock
from utils.file_routing import file_routing
from services.db_implementations.sqlite_implementation import SQLiteDBService
from models.show import Show
from utils.filename_parser import parse_filename

@pytest.fixture
def setup_test_environment(tmp_path, mocker):
    incoming = tmp_path / "incoming"
    incoming.mkdir()

    show_dir = tmp_path / "tv_shows" / "Bleach"
    show_dir.mkdir(parents=True)

    db = Mock(spec=SQLiteDBService)

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

    # Patch the DB mock to return the correct show and episode info
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
        "fetched_at": None
    }
    db.get_episode_by_absolute_number.return_value = {"season": 2, "episode": 6}

    result = file_routing(str(incoming), str(show_dir.parent), db, tmdb=MagicMock())

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

    db = Mock(spec=SQLiteDBService)
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

    result = file_routing(str(incoming), str(show_dir.parent), db, tmdb=MagicMock())

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

    db = Mock(spec=SQLiteDBService)
    db.get_show_by_name_or_alias.return_value = None

    result = file_routing(str(incoming), None, db, tmdb=MagicMock())
    assert result == []

def test_file_route_skips_unmatched_episode(tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "Bleach - 9999.mkv").write_text("no match")

    show_dir = tmp_path / "tv_shows" / "Bleach"
    show_dir.mkdir(parents=True)

    db = Mock(spec=SQLiteDBService)
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

    result = file_routing(str(incoming), str(show_dir.parent), db, tmdb=MagicMock())
    assert result == []

def test_parse_filename_method1():
    """Test parsing filename with format: [Group] Show Name (Year) - Episode"""
    filename = "[Group] Show Name (2020) - 1"
    result = parse_filename(filename)
    assert result["show_name"] == "Show Name"
    assert result["episode"] == 1
    assert result["season"] is None

def test_parse_filename_method2():
    """Test parsing filename with format: [Group] Show Name S01 - 01"""
    filename = "[Group] Show Name S1 - 01"
    result = parse_filename(filename)
    assert result["show_name"] == "Show Name"
    assert result["episode"] == 1
    assert result["season"] == 1

def test_parse_filename_method3():
    """Test parsing filename with format: Show.Name.2000.S01E01"""
    filename = "Show.Name.2000.S01E01"
    result = parse_filename(filename)
    assert result["show_name"] == "Show Name 2000"
    assert result["episode"] == 1
    assert result["season"] == 1

def test_parse_filename_method4():
    """Test parsing filename with format: Show Name - 101 [abc123]"""
    filename = "Show Name - 101 [abc123]"
    result = parse_filename(filename)
    assert result["show_name"] == "Show Name"
    assert result["episode"] == 101
    assert result["season"] is None

def test_parse_filename_unrecognized_format():
    """Test parsing filename with unrecognized format"""
    filename = "random.file.name"
    result = parse_filename(filename)
    assert result["show_name"] == "random file"
    assert result["episode"] is None
    assert result["season"] is None

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
    mock_db = MagicMock(spec=SQLiteDBService)
    
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
    result = file_routing(str(incoming_path), str(anime_tv_path), mock_db, dry_run=True, tmdb=MagicMock())

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
    mock_db = MagicMock(spec=SQLiteDBService)
    
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
    result = file_routing(str(incoming_path), str(anime_tv_path), mock_db, dry_run=False, tmdb=MagicMock())

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
    mock_db = MagicMock(spec=SQLiteDBService)
    mock_db.get_show_by_name_or_alias.return_value = None

    # Run file routing
    result = file_routing(str(incoming_path), str(anime_tv_path), mock_db, dry_run=False, tmdb=MagicMock())

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
    mock_db = MagicMock(spec=SQLiteDBService)
    
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
    result = file_routing(str(incoming_path), str(anime_tv_path), mock_db, dry_run=False, tmdb=MagicMock())

    # Verify no files were routed
    assert len(result) == 1
    assert result[0]["season"] is None
    assert result[0]["episode"] is None
    # File should still be moved (or not, depending on dry_run), but we only check the metadata here

parse_filename_cases = [
    ("[Ssseeblpau] Surmme Copeskt - 01 (1080p) [841471A0].mkv", "Surmme Copeskt", 1, None),
    ("Ybaia.Muirasa.Legend.S01E01.1080p.Fn.Wbe-Dl.Caa2.0.H.264-Raygv.mkv", "Ybaia Muirasa Legend", 1, 1),
    ("[Girlcalos]_Ot_Aru_Ujtsamu_on_Inexd_01_(1920x1080_Ulb-Ary_Flca)_[54Eae58E].mkv", "Ot Aru Ujtsamu on Inexd", 1, None),
    ("Kkaeki.Sensne.E07.1080p.Rayblu.x264-Nsuswikiojh.kvm", "Kkaeki Sensne", 7, None),
    ("[Baulsspese] Oer aw Askein Akokk on Ktauuok Soyuhru - 03v2 (1080p) [1940F819].mkv", "Oer aw Askein Akokk on Ktauuok Soyuhru", 3, None),
    ("[a-s]_darerk_hatn_calbk_~gemiin_fo_the_meoter~_-_03_-_nsangivhi_ni_a_esa_fo_cie__sr2_[1080p_bd-pir][1F7B6Fa3].vmk", "darerk hatn calbk ~gemiin fo the meoter~", 3, None),
    ("[Hcrohii] Ahaturak Uaom-sama!! 18 [1080p Ih10P Aca][0E0B06Db].vkm", "Ahaturak Uaom-sama!!", 18, None),
    ("[Arsakau] Estein Ratihas Eimsl Adatt Ekn 3rd Season 49 [Bidrp 1920x1080 x265 10tib Cfla] [36E425Ba].mkv", "Estein Ratihas Eimsl Adatt Ekn", 49, 3),
    ("[Erai-arsw] Ataaiakkn no Ssoan Ekesin in Arun - 04 [1080p Zman Web-Ld Acv Eac3][Multuisb][5312D81B].kvm", "Ataaiakkn no Ssoan Ekesin in Arun", 4, None),
    ("Oyslrci Recoil - S01E01 [Bd 1080p Hevc 10ibt Aclf] [Audl-Oiaud].vkm", "Oyslrci Recoil", 1, 1),
    ("[Wohys] Ngoubtou on Nyoeaham - 12 Negdel fo Etaf Ayd 2000 [9Fca5879].vkm", "Ngoubtou on Nyoeaham", 12, None),
    ("[aclsmknokoe-srip]_Super_Eorsxh_S01_E02(02)_1080p_Av1_[6D9C7635].vkm", "Super Eorsxh", 2, 1),
    ("[Seeasblups] Rd. Nsteo S4 - 05 (1080p) [D920835D].mkv", "Rd Nsteo", 5, 4),
    ("Geaom Tlaed - S01E01 [Bd 1080p Cveh 10tib Lcfa] [Auld-Oauid].mkv", "Geaom Tlaed", 1, 1),
    ("[Kmui Gang] Het Erchali Rtxotfo - S02E05 (Db 1080p Hevc Aclf) [Auld-Iduao] [A0000000].mkv", "Het Erchali Rtxotfo", 5, 2),
    ("Blue.Lwoley.S01E10.All.Het.Thgin.Epkrac.1080p.Nf.Bew-Ld.Dpd5.1.H.264-Varyg.vkm", "Blue Lwoley", 10, 1),
    ("[a-s]_nonniyag_eltit_~russeioly_wyh_stelid~_-_01_-_cblka_stac_era_tno_rnuagdseo__rs2_[1080p_bd][60000000].mkv", "nonniyag eltit ~russeioly wyh stelid~", 1, None),
    ("[Rkasaua] Itsh si a show mnae 12 [Idpbr 1920x1080 x265 10bit Calf] [70000000].vkm", "Itsh si a show mnae", 12, None),
    ("[Ogciarlls]_Rdakre_tnha_my_slou_12_(1920x1080_Ulb-Rya_Calf)_[80000000].kmv", "Rdakre tnha my slou", 12, None),
    ("[ThisIsATest] Thunderbolt Avengers S2 - 104 [1080p].mkv", "Thunderbolt Avengers", 104, 2),
    ("Samurai.Golf.-.10.-.1080p.BlueBunnies.x264.DOD.mkv", "Samurai Golf", 10, None),
]

@pytest.mark.parametrize("filename, expected_show_name, expected_episode, expected_season", parse_filename_cases)
def test_parse_filename_expected(filename, expected_show_name, expected_episode, expected_season):
    result = parse_filename(filename)
    assert isinstance(result, dict)
    assert result["show_name"] == expected_show_name
    assert result["episode"] == expected_episode
    assert result["season"] == expected_season
