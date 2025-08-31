"""
Unit tests for the Mock Service Factory.

These tests verify that the mock service factory creates properly functioning
mock services that implement all required abstract methods and provide
predictable test behavior.
"""

import pytest
import datetime
from typing import Dict, Any

from tests.utils.mock_service_factory import (
    MockServiceFactory,
    MockDatabaseService,
    MockLLMService,
    MockSFTPService,
    MockTMDBService
)
from services.db_implementations.db_interface import DatabaseInterface
from services.llm_implementations.llm_interface import LLMInterface
from models.show import Show
from models.episode import Episode
from models.downloaded_file import DownloadedFile, FileStatus


class TestMockDatabaseService:
    """Test the MockDatabaseService implementation."""
    
    def test_implements_database_interface(self):
        """Test that MockDatabaseService implements DatabaseInterface."""
        mock_db = MockDatabaseService()
        assert isinstance(mock_db, DatabaseInterface)
    
    def test_initialize_no_op(self):
        """Test that initialize method works without errors."""
        mock_db = MockDatabaseService()
        mock_db.initialize()  # Should not raise
    
    def test_add_and_retrieve_show(self):
        """Test adding and retrieving shows."""
        mock_db = MockDatabaseService()
        
        show = Show(
            sys_name="TestShow",
            sys_path="/test/path",
            tmdb_name="Test Show",
            tmdb_aliases="alias1, alias2",
            tmdb_id=123,
            tmdb_first_aired=datetime.datetime.now(),
            tmdb_last_aired=datetime.datetime.now(),
            tmdb_year=2020,
            tmdb_overview="Test overview",
            tmdb_season_count=2,
            tmdb_episode_count=20,
            tmdb_episode_groups="[]",
            tmdb_episodes_fetched_at=datetime.datetime.now(),
            tmdb_status="Ended",
            tmdb_external_ids="{}",
            fetched_at=datetime.datetime.now()
        )
        
        mock_db.add_show(show)
        
        # Test show exists
        assert mock_db.show_exists("TestShow")
        assert mock_db.show_exists("Test Show")
        assert mock_db.show_exists("alias1")
        assert mock_db.show_exists("alias2")
        assert not mock_db.show_exists("NonExistent")
        
        # Test get by sys_name
        retrieved = mock_db.get_show_by_sys_name("TestShow")
        assert retrieved is not None
        assert retrieved["sys_name"] == "TestShow"
        assert retrieved["tmdb_id"] == 123
        
        # Test get by name or alias
        retrieved = mock_db.get_show_by_name_or_alias("alias1")
        assert retrieved is not None
        assert retrieved["tmdb_name"] == "Test Show"
        
        # Test get by TMDB ID
        retrieved = mock_db.get_show_by_tmdb_id(123)
        assert retrieved is not None
        assert retrieved["tmdb_id"] == 123
        
        # Test get all shows
        all_shows = mock_db.get_all_shows()
        assert len(all_shows) == 1
        assert all_shows[0]["tmdb_id"] == 123
    
    def test_add_and_retrieve_episodes(self):
        """Test adding and retrieving episodes."""
        mock_db = MockDatabaseService()
        
        episode = Episode(
            tmdb_id=123,
            season=1,
            episode=1,
            abs_episode=1,
            episode_type="standard",
            episode_id=1001,
            air_date=datetime.datetime.now(),
            fetched_at=datetime.datetime.now(),
            name="Episode 1",
            overview="Episode overview"
        )
        
        mock_db.add_episode(episode)
        
        # Test episodes exist
        assert mock_db.episodes_exist(123)
        assert not mock_db.episodes_exist(999)
        
        # Test get episodes by TMDB ID
        episodes = mock_db.get_episodes_by_tmdb_id(123)
        assert len(episodes) == 1
        assert episodes[0]["episode"] == 1
        assert episodes[0]["name"] == "Episode 1"
    
    def test_add_multiple_episodes(self):
        """Test adding multiple episodes at once."""
        mock_db = MockDatabaseService()
        
        episodes = [
            Episode(
                tmdb_id=123,
                season=1,
                episode=i,
                abs_episode=i,
                episode_type="standard",
                episode_id=1000 + i,
                air_date=datetime.datetime.now(),
                fetched_at=datetime.datetime.now(),
                name=f"Episode {i}",
                overview=f"Episode {i} overview"
            )
            for i in range(1, 4)
        ]
        
        mock_db.add_episodes(episodes)
        
        retrieved_episodes = mock_db.get_episodes_by_tmdb_id(123)
        assert len(retrieved_episodes) == 3
        assert all(ep["tmdb_id"] == 123 for ep in retrieved_episodes)
    
    def test_file_operations(self):
        """Test file-related operations."""
        mock_db = MockDatabaseService()
        
        # Test downloaded files
        files = [
            {
                "name": "test_file.mkv",
                "path": "/remote/test_file.mkv",
                "size": 1000000,
                "modified_time": datetime.datetime.now(),
                "is_dir": False,
                "fetched_at": datetime.datetime.now()
            }
        ]
        
        mock_db.add_downloaded_files(files)
        downloaded = mock_db.get_downloaded_files()
        assert len(downloaded) == 1
        assert downloaded[0]["name"] == "test_file.mkv"
        
        # Test inventory files
        mock_db.add_inventory_files(files)
        inventory = mock_db.get_inventory_files()
        assert len(inventory) == 1
        assert inventory[0]["name"] == "test_file.mkv"
    
    def test_downloaded_file_object_operations(self):
        """Test DownloadedFile object operations."""
        mock_db = MockDatabaseService()
        
        downloaded_file = DownloadedFile(
            name="test.mkv",
            remote_path="/remote/test.mkv",
            current_path="/local/test.mkv",
            size=1000000,
            modified_time=datetime.datetime.now(),
            status=FileStatus.DOWNLOADED
        )
        
        # Test upsert
        result = mock_db.upsert_downloaded_file(downloaded_file)
        assert result.id is not None
        assert result.name == "test.mkv"
        
        # Test get by remote path
        retrieved = mock_db.get_downloaded_file_by_remote_path("/remote/test.mkv")
        assert retrieved is not None
        assert retrieved.name == "test.mkv"
        
        # Test get by status
        files_by_status = mock_db.get_downloaded_files_by_status(FileStatus.DOWNLOADED)
        assert len(files_by_status) == 1
        assert files_by_status[0].name == "test.mkv"
        
        # Test search
        results, total = mock_db.search_downloaded_files(q="test")
        assert total == 1
        assert len(results) == 1
        assert results[0].name == "test.mkv"
    
    def test_read_only_mode(self):
        """Test read-only mode functionality."""
        mock_db = MockDatabaseService(read_only=True)
        assert mock_db.is_read_only() is True
        
        mock_db = MockDatabaseService(read_only=False)
        assert mock_db.is_read_only() is False
    
    def test_backup_database(self):
        """Test database backup."""
        mock_db = MockDatabaseService()
        backup_path = mock_db.backup_database()
        assert isinstance(backup_path, str)
        assert backup_path.endswith(".db")


class TestMockLLMService:
    """Test the MockLLMService implementation."""
    
    def test_implements_llm_interface(self):
        """Test that MockLLMService implements LLMInterface."""
        mock_llm = MockLLMService()
        assert isinstance(mock_llm, LLMInterface)
    
    def test_parse_filename_basic(self):
        """Test basic filename parsing."""
        mock_llm = MockLLMService()
        
        result = mock_llm.parse_filename("Show.Name.S01E05.mkv")
        
        assert "show_name" in result
        assert "season" in result
        assert "episode" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert "filename" in result
        
        assert result["season"] == 1
        assert result["episode"] == 5
        assert result["confidence"] > 0.9
        assert result["filename"] == "Show.Name.S01E05.mkv"
    
    def test_parse_filename_custom_result(self):
        """Test setting custom parse results."""
        mock_llm = MockLLMService()
        
        custom_result = {
            "show_name": "Custom Show",
            "season": 2,
            "episode": 10,
            "confidence": 0.8,
            "reasoning": "Custom test result"
        }
        
        mock_llm.set_parse_result("custom_file.mkv", custom_result)
        result = mock_llm.parse_filename("custom_file.mkv")
        
        assert result["show_name"] == "Custom Show"
        assert result["season"] == 2
        assert result["episode"] == 10
        assert result["confidence"] == 0.8
    
    def test_batch_parse_filenames(self):
        """Test batch filename parsing."""
        mock_llm = MockLLMService()
        
        filenames = ["Show1.S01E01.mkv", "Show2.S02E03.mkv", "Show3.S01E02.mkv"]
        results = mock_llm.batch_parse_filenames(filenames)
        
        assert len(results) == 3
        assert all("show_name" in result for result in results)
        assert results[0]["season"] == 1
        assert results[0]["episode"] == 1
        assert results[1]["season"] == 2
        assert results[1]["episode"] == 3
    
    def test_suggest_short_dirname(self):
        """Test directory name shortening."""
        mock_llm = MockLLMService()
        
        # Short name should remain unchanged
        short_name = mock_llm.suggest_short_dirname("Short", max_length=20)
        assert short_name == "Short"
        
        # Long name should be truncated
        long_name = "This.Is.A.Very.Long.Directory.Name.That.Needs.Truncation"
        short_name = mock_llm.suggest_short_dirname(long_name, max_length=20)
        assert len(short_name) <= 20
        assert short_name.endswith("...")
    
    def test_suggest_short_filename(self):
        """Test filename shortening."""
        mock_llm = MockLLMService()
        
        # Short filename should remain unchanged
        short_name = mock_llm.suggest_short_filename("short.mkv", max_length=20)
        assert short_name == "short.mkv"
        
        # Long filename should be truncated but preserve extension
        long_name = "This.Is.A.Very.Long.Filename.That.Needs.Truncation.mkv"
        short_name = mock_llm.suggest_short_filename(long_name, max_length=20)
        assert len(short_name) <= 20
        assert short_name.endswith(".mkv")
        assert "..." in short_name
    
    def test_suggest_show_name(self):
        """Test show name suggestion from TMDB results."""
        mock_llm = MockLLMService()
        
        # Test with results
        detailed_results = [
            {"id": 123, "name": "Best Match Show"},
            {"id": 456, "name": "Second Match"}
        ]
        
        result = mock_llm.suggest_show_name("original name", detailed_results)
        
        assert "tmdb_id" in result
        assert "show_name" in result
        assert "confidence" in result
        assert "reasoning" in result
        
        assert result["tmdb_id"] == 123
        assert result["show_name"] == "Best Match Show"
        assert result["confidence"] > 0.8
        
        # Test with no results
        result = mock_llm.suggest_show_name("original name", [])
        assert result["tmdb_id"] is None
        assert result["show_name"] == "original name"
        assert result["confidence"] < 0.5


class TestMockSFTPService:
    """Test the MockSFTPService implementation."""
    
    def test_initialization(self):
        """Test SFTP service initialization."""
        mock_sftp = MockSFTPService("localhost", 22, "testuser", "/tmp/key")
        
        assert mock_sftp.host == "localhost"
        assert mock_sftp.port == 22
        assert mock_sftp.username == "testuser"
        assert mock_sftp.ssh_key_path == "/tmp/key"
    
    def test_context_manager(self):
        """Test SFTP service as context manager."""
        mock_sftp = MockSFTPService("localhost", 22, "testuser", "/tmp/key")
        
        with mock_sftp as sftp:
            assert sftp is mock_sftp
            # Should not raise any exceptions
    
    def test_list_remote_dir(self):
        """Test listing remote directory contents."""
        mock_sftp = MockSFTPService("localhost", 22, "testuser", "/tmp/key")
        
        files = mock_sftp.list_remote_dir("/remote")
        assert isinstance(files, list)
        # Should have some default files
        assert len(files) > 0
        
        # Check file structure
        for file_info in files:
            assert "name" in file_info
            assert "remote_path" in file_info
            assert "size" in file_info
            assert "modified_time" in file_info
            assert "is_dir" in file_info
            assert "fetched_at" in file_info
    
    def test_list_remote_files_recursive(self):
        """Test recursive file listing."""
        mock_sftp = MockSFTPService("localhost", 22, "testuser", "/tmp/key")
        
        files = mock_sftp.list_remote_files_recursive("/remote")
        assert isinstance(files, list)
        
        # Should only contain files, not directories
        for file_info in files:
            assert not file_info["is_dir"]
    
    def test_download_operations(self):
        """Test download operations."""
        mock_sftp = MockSFTPService("localhost", 22, "testuser", "/tmp/key")
        
        # Test file download (should not raise)
        mock_sftp.download_file("/remote/file.mkv", "/local/file.mkv")
        
        # Test directory download
        results = mock_sftp.download_dir("/remote/show1", "/local/show1")
        assert isinstance(results, list)
        
        # Results should have local_path added
        for result in results:
            assert "local_path" in result
    
    def test_add_mock_file(self):
        """Test adding mock files for testing."""
        mock_sftp = MockSFTPService("localhost", 22, "testuser", "/tmp/key")
        
        mock_sftp.add_mock_file("/remote/new_file.mkv", "new_file.mkv", size=2000000)
        
        files = mock_sftp.list_remote_files_recursive("/remote")
        new_files = [f for f in files if f["name"] == "new_file.mkv"]
        assert len(new_files) == 1
        assert new_files[0]["size"] == 2000000


class TestMockTMDBService:
    """Test the MockTMDBService implementation."""
    
    def test_initialization(self):
        """Test TMDB service initialization."""
        mock_tmdb = MockTMDBService("test_api_key")
        assert mock_tmdb.api_key == "test_api_key"
    
    def test_search_show(self):
        """Test show search functionality."""
        mock_tmdb = MockTMDBService("test_api_key")
        
        # Test default search
        result = mock_tmdb.search_show("some show")
        assert "results" in result
        assert len(result["results"]) > 0
        assert "id" in result["results"][0]
        assert "name" in result["results"][0]
        
        # Test predefined search
        result = mock_tmdb.search_show("mock show")
        assert result["results"][0]["id"] == 12345
        assert result["results"][0]["name"] == "Mock Show"
    
    def test_get_show_details(self):
        """Test getting show details."""
        mock_tmdb = MockTMDBService("test_api_key")
        
        details = mock_tmdb.get_show_details(123)
        
        assert "info" in details
        assert "episode_groups" in details
        assert "alternative_titles" in details
        assert "external_ids" in details
        
        info = details["info"]
        assert info["id"] == 123
        assert "name" in info
        assert "number_of_seasons" in info
        assert "number_of_episodes" in info
    
    def test_get_season_details(self):
        """Test getting season details."""
        mock_tmdb = MockTMDBService("test_api_key")
        
        season = mock_tmdb.get_show_season_details(123, 1)
        
        assert "id" in season
        assert "season_number" in season
        assert "episodes" in season
        assert season["season_number"] == 1
        assert len(season["episodes"]) == 10  # Default 10 episodes
        
        # Check episode structure
        episode = season["episodes"][0]
        assert "episode_number" in episode
        assert "id" in episode
        assert "name" in episode
        assert "overview" in episode
    
    def test_get_episode_details(self):
        """Test getting episode details."""
        mock_tmdb = MockTMDBService("test_api_key")
        
        episode = mock_tmdb.get_show_episode_details(123, 1, 5)
        
        assert episode["episode_number"] == 5
        assert episode["season_number"] == 1
        assert episode["show_id"] == 123
        assert "id" in episode
        assert "name" in episode
        assert "overview" in episode
    
    def test_add_mock_show(self):
        """Test adding custom mock shows."""
        mock_tmdb = MockTMDBService("test_api_key")
        
        custom_show = {
            "id": 999,
            "name": "Custom Test Show",
            "first_air_date": "2021-01-01"
        }
        
        mock_tmdb.add_mock_show("custom show", custom_show)
        
        result = mock_tmdb.search_show("custom show")
        assert result["results"][0]["id"] == 999
        assert result["results"][0]["name"] == "Custom Test Show"


class TestMockServiceFactory:
    """Test the MockServiceFactory class."""
    
    def test_create_mock_db_service(self):
        """Test creating mock database service."""
        config = {"database": {"type": "sqlite"}}
        
        db_service = MockServiceFactory.create_mock_db_service(config)
        assert isinstance(db_service, MockDatabaseService)
        assert isinstance(db_service, DatabaseInterface)
        assert not db_service.is_read_only()
        
        # Test read-only mode
        db_service_ro = MockServiceFactory.create_mock_db_service(config, read_only=True)
        assert db_service_ro.is_read_only()
    
    def test_create_mock_llm_service(self):
        """Test creating mock LLM service."""
        config = {"llm": {"service": "ollama"}}
        
        llm_service = MockServiceFactory.create_mock_llm_service(config)
        assert isinstance(llm_service, MockLLMService)
        assert isinstance(llm_service, LLMInterface)
        assert llm_service.config == config
    
    def test_create_mock_sftp_service(self):
        """Test creating mock SFTP service."""
        config = {
            "sftp": {
                "host": "test.example.com",
                "port": "2222",
                "username": "testuser",
                "ssh_key_path": "/test/key"
            }
        }
        
        sftp_service = MockServiceFactory.create_mock_sftp_service(config)
        assert isinstance(sftp_service, MockSFTPService)
        assert sftp_service.host == "test.example.com"
        assert sftp_service.port == 2222
        assert sftp_service.username == "testuser"
        assert sftp_service.ssh_key_path == "/test/key"
    
    def test_create_mock_tmdb_service(self):
        """Test creating mock TMDB service."""
        config = {"tmdb": {"api_key": "test_key_123"}}
        
        tmdb_service = MockServiceFactory.create_mock_tmdb_service(config)
        assert isinstance(tmdb_service, MockTMDBService)
        assert tmdb_service.api_key == "test_key_123"
    
    def test_create_all_mock_services(self):
        """Test creating all mock services at once."""
        config = {
            "database": {"type": "sqlite"},
            "llm": {"service": "ollama"},
            "sftp": {
                "host": "localhost",
                "port": "22",
                "username": "testuser",
                "ssh_key_path": "/tmp/key"
            },
            "tmdb": {"api_key": "test_key"}
        }
        
        services = MockServiceFactory.create_all_mock_services(config)
        
        assert "db" in services
        assert "llm_service" in services
        assert "sftp" in services
        assert "tmdb" in services
        
        assert isinstance(services["db"], MockDatabaseService)
        assert isinstance(services["llm_service"], MockLLMService)
        assert isinstance(services["sftp"], MockSFTPService)
        assert isinstance(services["tmdb"], MockTMDBService)
    
    def test_create_mock_context_object(self):
        """Test creating complete mock context object for CLI testing."""
        config = {
            "database": {"type": "sqlite"},
            "llm": {"service": "ollama"},
            "sftp": {
                "host": "localhost",
                "port": "22",
                "username": "testuser",
                "ssh_key_path": "/tmp/key"
            },
            "tmdb": {"api_key": "test_key"},
            "routing": {"anime_tv_path": "/test/anime"},
            "transfers": {"incoming": "/test/incoming"}
        }
        
        context = MockServiceFactory.create_mock_context_object(config)
        
        # Check all required context keys
        required_keys = [
            "config", "db", "llm_service", "sftp", "tmdb",
            "anime_tv_path", "incoming_path", "dry_run"
        ]
        
        for key in required_keys:
            assert key in context
        
        # Check service types
        assert isinstance(context["db"], MockDatabaseService)
        assert isinstance(context["llm_service"], MockLLMService)
        assert isinstance(context["sftp"], MockSFTPService)
        assert isinstance(context["tmdb"], MockTMDBService)
        
        # Check paths
        assert context["anime_tv_path"] == "/test/anime"
        assert context["incoming_path"] == "/test/incoming"
        assert context["dry_run"] is False
        
        # Test with overrides
        context_with_overrides = MockServiceFactory.create_mock_context_object(
            config,
            dry_run=True,
            anime_tv_path="/override/anime"
        )
        
        assert context_with_overrides["dry_run"] is True
        assert context_with_overrides["anime_tv_path"] == "/override/anime"
        assert context_with_overrides["db"].is_read_only() is True  # Should be read-only when dry_run=True
    
    def test_config_case_insensitive_access(self):
        """Test that factory handles both uppercase and lowercase config sections."""
        # Test uppercase config sections (legacy format)
        config_upper = {
            "Database": {"type": "sqlite"},
            "LLM": {"service": "ollama"},
            "SFTP": {
                "host": "localhost",
                "port": "22",
                "username": "testuser",
                "ssh_key_path": "/tmp/key"
            },
            "TMDB": {"api_key": "test_key"},
            "Routing": {"anime_tv_path": "/test/anime"},
            "Transfers": {"incoming": "/test/incoming"}
        }
        
        services_upper = MockServiceFactory.create_all_mock_services(config_upper)
        context_upper = MockServiceFactory.create_mock_context_object(config_upper)
        
        # Should work the same as lowercase
        assert isinstance(services_upper["db"], MockDatabaseService)
        assert isinstance(services_upper["sftp"], MockSFTPService)
        assert context_upper["anime_tv_path"] == "/test/anime"
        
        # Test lowercase config sections (normalized format)
        config_lower = {
            "database": {"type": "sqlite"},
            "llm": {"service": "ollama"},
            "sftp": {
                "host": "localhost",
                "port": "22",
                "username": "testuser",
                "ssh_key_path": "/tmp/key"
            },
            "tmdb": {"api_key": "test_key"},
            "routing": {"anime_tv_path": "/test/anime"},
            "transfers": {"incoming": "/test/incoming"}
        }
        
        services_lower = MockServiceFactory.create_all_mock_services(config_lower)
        context_lower = MockServiceFactory.create_mock_context_object(config_lower)
        
        # Should work the same as uppercase
        assert isinstance(services_lower["db"], MockDatabaseService)
        assert isinstance(services_lower["sftp"], MockSFTPService)
        assert context_lower["anime_tv_path"] == "/test/anime"