"""
Test configuration factory for creating standardized test configurations.

This module provides utilities for creating valid and invalid test configurations
that are compatible with the normalized configuration system and test requirements.
"""

import os
import tempfile
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime


class TestConfigFactory:
    """
    Factory class for creating standardized test configurations.
    
    Provides methods for creating valid base configurations, configuration overrides,
    and invalid configurations for testing validation logic.
    """
    
    @staticmethod
    def create_base_config() -> Dict[str, Dict[str, Any]]:
        """
        Create a complete base configuration for tests.
        
        Returns:
            Dict[str, Dict[str, Any]]: Complete normalized test configuration
        """
        temp_dir = Path(tempfile.gettempdir()) / "test_sync2nas"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "database": {
                "type": "sqlite"
            },
            "sqlite": {
                "db_file": str(temp_dir / "test.db")
            },
            "llm": {
                "service": "ollama"
            },
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "qwen3:14b",
                "timeout": "30",
                "num_ctx": "2048"
            },
            "openai": {
                "api_key": "test-openai-key",
                "model": "qwen3:14b",
                "max_tokens": "1000",
                "temperature": "0.7"
            },
            "anthropic": {
                "api_key": "test-anthropic-key", 
                "model": "qwen3:14b",
                "max_tokens": "1000",
                "temperature": "0.7"
            },
            "sftp": {
                "host": "localhost",
                "port": "22",
                "username": "testuser",
                "ssh_key_path": str(temp_dir / "test_key"),
                "paths": "/remote/path"
            },
            "tmdb": {
                "api_key": "test_tmdb_api_key"
            },
            "transfers": {
                "incoming": str(temp_dir / "incoming")
            },
            "routing": {
                "anime_tv_path": str(temp_dir / "anime_tv")
            }
        }
    
    @staticmethod
    def create_config_with_overrides(**overrides) -> Dict[str, Dict[str, Any]]:
        """
        Create configuration with specific overrides.
        
        Args:
            **overrides: Section-level overrides in format section_key=value_dict
                        or nested overrides in format section__key=value
        
        Returns:
            Dict[str, Dict[str, Any]]: Configuration with applied overrides
        """
        config = TestConfigFactory.create_base_config()
        
        for key, value in overrides.items():
            if "__" in key:
                # Handle nested overrides like llm__service="openai"
                section, config_key = key.split("__", 1)
                if section not in config:
                    config[section] = {}
                config[section][config_key] = value
            else:
                # Handle section-level overrides
                if isinstance(value, dict):
                    if key not in config:
                        config[key] = {}
                    config[key].update(value)
                else:
                    # Single value override - assume it's for the section itself
                    config[key] = value
        
        return config
    
    @staticmethod
    def create_invalid_config(invalid_section: str) -> Dict[str, Dict[str, Any]]:
        """
        Create configuration with specific invalid sections for testing validation logic.
        
        Args:
            invalid_section: Which section to make invalid
            
        Returns:
            Dict[str, Dict[str, Any]]: Configuration with invalid section
        """
        config = TestConfigFactory.create_base_config()
        
        if invalid_section == "database":
            config["database"] = {"type": "invalid_db_type"}
        elif invalid_section == "sqlite":
            config["sqlite"] = {"db_file": ""}  # Empty db_file
        elif invalid_section == "llm":
            config["llm"] = {"service": "invalid_llm_service"}
        elif invalid_section == "ollama":
            config["ollama"] = {"model": "qwen3:14b"}  # Empty model
        elif invalid_section == "openai":
            config["openai"] = {"api_key": ""}  # Empty API key
        elif invalid_section == "anthropic":
            config["anthropic"] = {"api_key": ""}  # Empty API key
        elif invalid_section == "sftp":
            config["sftp"] = {"host": ""}  # Empty host
        elif invalid_section == "tmdb":
            config["tmdb"] = {"api_key": ""}  # Empty API key
        elif invalid_section == "transfers":
            config["transfers"] = {"incoming": ""}  # Empty path
        elif invalid_section == "routing":
            config["routing"] = {"anime_tv_path": ""}  # Empty path
        elif invalid_section == "missing_required":
            # Remove required sections
            del config["database"]
            del config["llm"]
        else:
            raise ValueError(f"Unknown invalid section type: {invalid_section}")
        
        return config
    
    @staticmethod
    def create_minimal_config() -> Dict[str, Dict[str, Any]]:
        """
        Create minimal valid configuration with only required sections.
        
        Returns:
            Dict[str, Dict[str, Any]]: Minimal valid configuration
        """
        temp_dir = Path(tempfile.gettempdir()) / "test_sync2nas_minimal"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "database": {
                "type": "sqlite"
            },
            "sqlite": {
                "db_file": str(temp_dir / "minimal_test.db")
            },
            "llm": {
                "service": "ollama"
            },
            "ollama": {
                "model": "qwen3:14b"
            }
        }
    
    @staticmethod
    def create_memory_db_config() -> Dict[str, Dict[str, Any]]:
        """
        Create configuration using in-memory SQLite database for fast tests.
        
        Returns:
            Dict[str, Dict[str, Any]]: Configuration with in-memory database
        """
        return TestConfigFactory.create_config_with_overrides(
            sqlite__db_file=":memory:"
        )
    
    @staticmethod
    def create_llm_service_configs() -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Create configurations for all supported LLM services.
        
        Returns:
            Dict[str, Dict[str, Dict[str, Any]]]: Configurations keyed by service name
        """
        base_config = TestConfigFactory.create_base_config()
        
        return {
            "ollama": TestConfigFactory.create_config_with_overrides(
                llm__service="ollama"
            ),
            "openai": TestConfigFactory.create_config_with_overrides(
                llm__service="openai"
            ),
            "anthropic": TestConfigFactory.create_config_with_overrides(
                llm__service="anthropic"
            )
        }
    
    @staticmethod
    def create_configparser_format(config_dict: Dict[str, Dict[str, Any]]) -> configparser.ConfigParser:
        """
        Convert normalized config dict to ConfigParser format for legacy compatibility.
        
        Args:
            config_dict: Normalized configuration dictionary
            
        Returns:
            configparser.ConfigParser: Configuration in ConfigParser format
        """
        parser = configparser.ConfigParser()
        
        for section_name, section_data in config_dict.items():
            # Convert section name to title case for ConfigParser compatibility
            parser_section_name = section_name.title()
            parser[parser_section_name] = {}
            
            for key, value in section_data.items():
                parser[parser_section_name][key] = str(value)
        
        return parser
    
    @staticmethod
    def write_config_file(
        config_dict: Dict[str, Dict[str, Any]], 
        file_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Write configuration to a temporary file.
        
        Args:
            config_dict: Configuration dictionary to write
            file_path: Optional path to write to, creates temp file if None
            
        Returns:
            Path: Path to the written configuration file
        """
        if file_path is None:
            temp_dir = Path(tempfile.gettempdir()) / "test_sync2nas_configs"
            temp_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_path = temp_dir / f"test_config_{timestamp}.ini"
        
        file_path = Path(file_path)
        
        # Convert to ConfigParser format and write
        parser = TestConfigFactory.create_configparser_format(config_dict)
        
        with open(file_path, 'w') as f:
            parser.write(f)
        
        return file_path
    
    @staticmethod
    def create_test_directories(config_dict: Dict[str, Dict[str, Any]]) -> Dict[str, Path]:
        """
        Create test directories referenced in configuration.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Dict[str, Path]: Created directory paths keyed by purpose
        """
        created_dirs = {}
        
        # Create directories from configuration paths
        path_mappings = [
            ("transfers", "incoming", "incoming_dir"),
            ("routing", "anime_tv_path", "anime_tv_dir"),
        ]
        
        for section, key, dir_key in path_mappings:
            if section in config_dict and key in config_dict[section]:
                dir_path = Path(config_dict[section][key])
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs[dir_key] = dir_path
        
        # Create SSH key directory if specified
        if "sftp" in config_dict and "ssh_key_path" in config_dict["sftp"]:
            ssh_key_path = Path(config_dict["sftp"]["ssh_key_path"])
            ssh_key_dir = ssh_key_path.parent
            ssh_key_dir.mkdir(parents=True, exist_ok=True)
            created_dirs["ssh_key_dir"] = ssh_key_dir
        
        return created_dirs
    
    @staticmethod
    def get_validation_test_cases() -> List[Dict[str, Any]]:
        """
        Get test cases for configuration validation testing.
        
        Returns:
            List[Dict[str, Any]]: Test cases with config and expected validation result
        """
        return [
            {
                "name": "valid_base_config",
                "config": TestConfigFactory.create_base_config(),
                "should_be_valid": True,
                "expected_errors": []
            },
            {
                "name": "invalid_database_type",
                "config": TestConfigFactory.create_invalid_config("database"),
                "should_be_valid": False,
                "expected_errors": ["database.type"]
            },
            {
                "name": "empty_sqlite_db_file",
                "config": TestConfigFactory.create_invalid_config("sqlite"),
                "should_be_valid": False,
                "expected_errors": ["sqlite.db_file"]
            },
            {
                "name": "invalid_llm_service",
                "config": TestConfigFactory.create_invalid_config("llm"),
                "should_be_valid": False,
                "expected_errors": ["llm.service"]
            },
            {
                "name": "empty_ollama_model",
                "config": TestConfigFactory.create_invalid_config("ollama"),
                "should_be_valid": False,
                "expected_errors": ["ollama.model"]
            },
            {
                "name": "missing_required_sections",
                "config": TestConfigFactory.create_invalid_config("missing_required"),
                "should_be_valid": False,
                "expected_errors": ["database", "llm"]
            }
        ]


class MockServiceFactory:
    """
    Factory for creating mock services for testing.
    
    Provides standardized mock service creation with predictable test behavior
    without external dependencies.
    """
    
    @staticmethod
    def create_mock_llm_service(config: Dict[str, Any], service_type: str = "ollama"):
        """
        Create mock LLM service with all abstract methods implemented.
        
        Args:
            config: Configuration dictionary
            service_type: Type of LLM service to mock
            
        Returns:
            Mock LLM service instance
        """
        from unittest.mock import Mock
        from services.llm_implementations.base_llm_service import BaseLLMService
        
        mock_service = Mock(spec=BaseLLMService)
        
        # Set up standard mock responses
        mock_service.parse_filename.return_value = {
            "show_name": "Test Show",
            "season": 1,
            "episode": 1,
            "confidence": 0.9,
            "episode_type": "standard"
        }
        
        mock_service.suggest_show_name.return_value = {
            "tmdb_id": 123,
            "show_name": "Test Show",
            "confidence": 0.9,
            "reasoning": "Mock suggestion"
        }
        
        def mock_batch_parse(filenames):
            return [
                {
                    "filename": filename,
                    "parsed": {
                        "show_name": "Test Show",
                        "season": 1,
                        "episode": 1,
                        "confidence": 0.9,
                        "episode_type": "standard"
                    }
                }
                for filename in filenames
            ]
        
        mock_service.batch_parse_filenames.side_effect = mock_batch_parse
        
        # Set service properties
        mock_service.service_type = service_type
        mock_service.model = config.get(service_type, {}).get("model", "test-model")
        
        return mock_service
    
    @staticmethod
    def create_mock_db_service(db_path: str = ":memory:"):
        """
        Create mock database service for tests.
        
        Args:
            db_path: Database path (defaults to in-memory)
            
        Returns:
            Mock database service instance
        """
        from unittest.mock import Mock
        from services.db_implementations.db_interface import DatabaseInterface
        
        mock_db = Mock(spec=DatabaseInterface)
        
        # Set up standard mock responses
        mock_db.show_exists.return_value = False
        mock_db.episodes_exist.return_value = False
        mock_db.get_all_shows.return_value = []
        mock_db.get_downloaded_files.return_value = []
        mock_db.get_inventory_files.return_value = []
        
        # Mock successful operations
        mock_db.add_show.return_value = None
        mock_db.add_episode.return_value = None
        mock_db.initialize.return_value = None
        
        return mock_db
    
    @staticmethod
    def create_mock_sftp_service(config: Dict[str, Any]):
        """
        Create mock SFTP service for tests.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Mock SFTP service instance
        """
        from unittest.mock import Mock, MagicMock
        from services.sftp_service import SFTPService
        
        mock_sftp = MagicMock(spec=SFTPService)
        
        # Set up service properties
        sftp_config = config.get("sftp", {})
        mock_sftp.host = sftp_config.get("host", "localhost")
        mock_sftp.port = int(sftp_config.get("port", 22))
        mock_sftp.username = sftp_config.get("username", "testuser")
        mock_sftp.ssh_key_path = sftp_config.get("ssh_key_path", "/tmp/test_key")
        
        # Set up standard mock responses
        mock_sftp.list_remote_dir.return_value = [
            {
                "name": "test_file.mkv",
                "path": "/remote/test_file.mkv",
                "size": 1000000,
                "modified_time": "2024-01-01 12:00:00",
                "is_dir": False,
                "fetched_at": "2024-01-01 12:00:00"
            }
        ]
        
        mock_sftp.list_remote_files_recursive.return_value = [
            {
                "name": "test_file.mkv",
                "path": "/remote/test_file.mkv", 
                "size": 1000000,
                "modified_time": "2024-01-01 12:00:00",
                "is_dir": False,
                "fetched_at": "2024-01-01 12:00:00"
            }
        ]
        
        mock_sftp.download_file.return_value = True
        mock_sftp.download_dir.return_value = True
        
        # Set up context manager behavior
        mock_sftp.__enter__.return_value = mock_sftp
        mock_sftp.__exit__.return_value = None
        
        return mock_sftp
