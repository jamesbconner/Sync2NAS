"""
Basic tests for the Sync2NAS GUI functionality.
"""

import pytest
import tkinter as tk
import sys
import os
import tempfile
import configparser
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import from the main project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestGUIBasic:
    """Basic GUI tests that don't require full GUI initialization"""
    
    def test_ttkbootstrap_import(self):
        """Test that ttkbootstrap import works correctly"""
        try:
            from gui.main import TTKBOOTSTRAP_AVAILABLE
            assert isinstance(TTKBOOTSTRAP_AVAILABLE, bool)
        except ImportError as e:
            pytest.fail(f"Failed to import TTKBOOTSTRAP_AVAILABLE: {e}")
    
    def test_gui_class_import(self):
        """Test that the GUI class can be imported"""
        try:
            from gui.main import Sync2NASGUI
            assert Sync2NASGUI is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Sync2NASGUI: {e}")
    
    def test_gui_instantiation_basic(self, root_window):
        """Test basic GUI instantiation without full widget creation"""
        try:
            from gui.main import Sync2NASGUI
            
            # Create the GUI instance using the fixture
            gui = Sync2NASGUI(root_window)
            
            # Verify basic attributes
            assert gui is not None
            assert hasattr(gui, 'root')
            assert hasattr(gui, 'config_path')
            assert hasattr(gui, 'dry_run')
            assert hasattr(gui, 'verbose_level_str')
            assert hasattr(gui, 'max_workers')
            assert hasattr(gui, 'use_llm')
            assert hasattr(gui, 'llm_confidence')
            assert hasattr(gui, 'auto_add_shows')
            assert hasattr(gui, 'llm_service')
            assert hasattr(gui, 'llm_model')
            assert hasattr(gui, 'db_type')
            assert hasattr(gui, 'sftp_port')
            assert hasattr(gui, 'postgres_port')
            assert hasattr(gui, 'milvus_port')
            
        except Exception as e:
            pytest.fail(f"Failed to instantiate GUI: {e}")
    
    def test_verbosity_flags(self, root_window):
        """Test verbosity flag generation"""
        try:
            from gui.main import Sync2NASGUI
            
            gui = Sync2NASGUI(root_window)
            
            # Test WARNING level
            gui.verbose_level_str.set("WARNING")
            flags = gui.get_verbosity_flags()
            assert flags == []
            
            # Test INFO level
            gui.verbose_level_str.set("INFO")
            flags = gui.get_verbosity_flags()
            assert flags == ["-v"]
            
            # Test DEBUG level
            gui.verbose_level_str.set("DEBUG")
            flags = gui.get_verbosity_flags()
            assert flags == ["-v", "-v"]
            
        except Exception as e:
            pytest.fail(f"Failed to test verbosity flags: {e}")
    
    def test_config_overrides(self, root_window):
        """Test configuration override functionality"""
        try:
            from gui.main import Sync2NASGUI
            
            gui = Sync2NASGUI(root_window)
            
            # Test applying overrides
            gui.sftp_host.set("testhost")
            gui.sftp_username.set("testuser")
            gui.tmdb_api_key.set("testkey")
            
            gui.apply_config_overrides()
            
            # Check that overrides were applied
            assert gui.config_overrides["SFTP"]["host"] == "testhost"
            assert gui.config_overrides["SFTP"]["username"] == "testuser"
            assert gui.config_overrides["TMDB"]["api_key"] == "testkey"
            
            # Test clearing overrides
            gui.clear_config_overrides()
            assert gui.config_overrides == {}
            assert gui.temp_config_file is None
            
        except Exception as e:
            pytest.fail(f"Failed to test config overrides: {e}")
    
    def test_get_config_path_for_command(self, root_window):
        """Test getting config path for CLI commands"""
        try:
            from gui.main import Sync2NASGUI
            
            gui = Sync2NASGUI(root_window)
            
            # Test with no overrides
            path = gui.get_config_path_for_command()
            assert path == "./config/sync2nas_config.ini"
            
            # Test with overrides
            gui.sftp_host.set("testhost")
            gui.apply_config_overrides()
            path = gui.get_config_path_for_command()
            assert path is not None
            assert path != "./config/sync2nas_config.ini"
            
        except Exception as e:
            pytest.fail(f"Failed to test get_config_path_for_command: {e}")
    
    @patch('tkinter.filedialog.askopenfilename')
    def test_browse_functions(self, mock_askopenfilename, root_window):
        """Test browse functions with mocked file dialogs"""
        try:
            from gui.main import Sync2NASGUI
            
            gui = Sync2NASGUI(root_window)
            
            # Test browse_config
            mock_askopenfilename.return_value = "/test/path/config.ini"
            gui.browse_config()
            assert gui.config_path.get() == "/test/path/config.ini"
            
            # Test browse_sqlite_db
            mock_askopenfilename.return_value = "/test/path/db.sqlite"
            gui.browse_sqlite_db()
            assert gui.sqlite_db_file.get() == "/test/path/db.sqlite"
            
            # Test browse_ssh_key
            mock_askopenfilename.return_value = "/test/path/key.pem"
            gui.browse_ssh_key()
            assert gui.sftp_ssh_key_path.get() == "/test/path/key.pem"
            
        except Exception as e:
            pytest.fail(f"Failed to test browse functions: {e}")
    
    @patch('tkinter.filedialog.askdirectory')
    def test_browse_directory_functions(self, mock_askdirectory, root_window):
        """Test browse directory functions with mocked dialogs"""
        try:
            from gui.main import Sync2NASGUI
            
            gui = Sync2NASGUI(root_window)
            
            # Test browse_incoming
            mock_askdirectory.return_value = "/test/incoming"
            gui.browse_incoming()
            assert gui.incoming_path.get() == "/test/incoming"
            
            # Test browse_anime_tv_path
            mock_askdirectory.return_value = "/test/anime_tv"
            gui.browse_anime_tv_path()
            assert gui.anime_tv_path.get() == "/test/anime_tv"
            
        except Exception as e:
            pytest.fail(f"Failed to test browse directory functions: {e}")
    
    def test_callback_functions(self, root_window):
        """Test callback functions"""
        try:
            from gui.main import Sync2NASGUI
            
            gui = Sync2NASGUI(root_window)
            
            # Test LLM service change callback
            gui.llm_service.set("openai")
            gui.on_llm_service_change()
            
            gui.llm_service.set("anthropic")
            gui.on_llm_service_change()
            
            gui.llm_service.set("ollama")
            gui.on_llm_service_change()
            
            # Test database type change callback
            gui.db_type.set("sqlite")
            gui.on_db_type_change()
            
            gui.db_type.set("postgres")
            gui.on_db_type_change()
            
            gui.db_type.set("milvus")
            gui.on_db_type_change()
            
        except Exception as e:
            pytest.fail(f"Failed to test callback functions: {e}")
    
    def test_state_management(self, root_window):
        """Test state management functions without threading"""
        try:
            from gui.main import Sync2NASGUI
            
            gui = Sync2NASGUI(root_window)
            
            # Test download state
            assert gui.is_downloading is False
            gui.is_downloading = True
            assert gui.is_downloading is True
            gui.finish_download()
            assert gui.is_downloading is False
            
            # Test routing state
            assert gui.is_routing is False
            gui.is_routing = True
            assert gui.is_routing is True
            gui.finish_routing()
            assert gui.is_routing is False
            
            # Test search states (only test the state changes, not the threaded operations)
            # For search operations, we'll only test the state flags without starting threads
            gui.is_searching_shows = False
            gui.is_searching_shows = True
            assert gui.is_searching_shows is True
            gui.finish_show_search()
            assert gui.is_searching_shows is False
            
            gui.is_searching_tmdb = False
            gui.is_searching_tmdb = True
            assert gui.is_searching_tmdb is True
            gui.finish_tmdb_search()
            assert gui.is_searching_tmdb is False
            
            # Test add/fix show states
            gui.start_add_show()
            gui.finish_add_show()
            
            gui.start_fix_show()
            gui.finish_fix_show()
            
            # Test database operation states
            gui.start_init_db()
            gui.finish_init_db()
            
            gui.start_backup_db()
            gui.finish_backup_db()
            
            gui.start_update_episodes()
            gui.finish_update_episodes()
            
            # Test bootstrap states
            gui.start_bootstrap_tv_shows()
            gui.finish_bootstrap_tv_shows()
            
            gui.start_bootstrap_episodes()
            gui.finish_bootstrap_episodes()
            
            gui.start_bootstrap_downloads()
            gui.finish_bootstrap_downloads()
            
            gui.start_bootstrap_inventory()
            gui.finish_bootstrap_inventory()
            
        except Exception as e:
            pytest.fail(f"Failed to test state management: {e}")


if __name__ == "__main__":
    pytest.main([__file__]) 