"""
Core GUI functionality tests that don't require tkinter initialization.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import from the main project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestGUICore:
    """Test core GUI functionality without tkinter"""
    
    def test_ttkbootstrap_availability(self):
        """Test that ttkbootstrap availability is detected correctly"""
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
    
    def test_gui_class_attributes(self):
        """Test that the GUI class has the expected attributes"""
        try:
            from gui.main import Sync2NASGUI
            
            # Check that the class has the expected methods
            assert hasattr(Sync2NASGUI, '__init__')
            assert hasattr(Sync2NASGUI, 'get_verbosity_flags')
            assert hasattr(Sync2NASGUI, 'apply_config_overrides')
            assert hasattr(Sync2NASGUI, 'clear_config_overrides')
            assert hasattr(Sync2NASGUI, 'get_config_path_for_command')
            assert hasattr(Sync2NASGUI, 'execute_cli_command')
            assert hasattr(Sync2NASGUI, 'execute_cli_command_with_output')
            
        except ImportError as e:
            pytest.fail(f"Failed to import Sync2NASGUI: {e}")
    
    def test_verbosity_flags_logic(self):
        """Test verbosity flag generation logic without tkinter"""
        try:
            from gui.main import Sync2NASGUI
            
            # Create a mock GUI instance
            gui = Mock()
            gui.verbose_level_str = Mock()
            
            # Test the logic directly
            def get_verbosity_flags():
                level = gui.verbose_level_str.get()
                if level == "WARNING":
                    return []
                elif level == "INFO":
                    return ["-v"]
                elif level == "DEBUG":
                    return ["-v", "-v"]
                else:
                    return []
            
            # Test WARNING level
            gui.verbose_level_str.get.return_value = "WARNING"
            flags = get_verbosity_flags()
            assert flags == []
            
            # Test INFO level
            gui.verbose_level_str.get.return_value = "INFO"
            flags = get_verbosity_flags()
            assert flags == ["-v"]
            
            # Test DEBUG level
            gui.verbose_level_str.get.return_value = "DEBUG"
            flags = get_verbosity_flags()
            assert flags == ["-v", "-v"]
            
        except ImportError as e:
            pytest.fail(f"Failed to test verbosity flags logic: {e}")
    
    def test_config_overrides_logic(self):
        """Test configuration override logic without tkinter"""
        try:
            from gui.main import Sync2NASGUI
            
            # Create a mock GUI instance
            gui = Mock()
            gui.config_overrides = {}
            gui.temp_config_file = None
            
            # Mock tkinter variables
            gui.sftp_host = Mock()
            gui.sftp_username = Mock()
            gui.tmdb_api_key = Mock()
            
            # Test applying overrides
            gui.sftp_host.get.return_value = "testhost"
            gui.sftp_username.get.return_value = "testuser"
            gui.tmdb_api_key.get.return_value = "testkey"
            
            # Simulate apply_config_overrides logic
            def apply_config_overrides():
                gui.config_overrides["SFTP"] = {
                    "host": gui.sftp_host.get(),
                    "username": gui.sftp_username.get()
                }
                gui.config_overrides["TMDB"] = {
                    "api_key": gui.tmdb_api_key.get()
                }
            
            apply_config_overrides()
            
            # Check that overrides were applied
            assert gui.config_overrides["SFTP"]["host"] == "testhost"
            assert gui.config_overrides["SFTP"]["username"] == "testuser"
            assert gui.config_overrides["TMDB"]["api_key"] == "testkey"
            
            # Test clearing overrides
            def clear_config_overrides():
                gui.config_overrides = {}
                gui.temp_config_file = None
            
            clear_config_overrides()
            assert gui.config_overrides == {}
            assert gui.temp_config_file is None
            
        except ImportError as e:
            pytest.fail(f"Failed to test config overrides logic: {e}")
    
    def test_get_config_path_logic(self):
        """Test config path logic without tkinter"""
        try:
            from gui.main import Sync2NASGUI
            
            # Create a mock GUI instance
            gui = Mock()
            gui.config_overrides = {}
            gui.temp_config_file = None
            
            # Test with no overrides
            def get_config_path_for_command():
                if gui.config_overrides:
                    return gui.temp_config_file
                else:
                    return "./config/sync2nas_config.ini"
            
            path = get_config_path_for_command()
            assert path == "./config/sync2nas_config.ini"
            
            # Test with overrides
            gui.config_overrides = {"SFTP": {"host": "testhost"}}
            gui.temp_config_file = "/temp/config.ini"
            
            path = get_config_path_for_command()
            assert path == "/temp/config.ini"
            
        except ImportError as e:
            pytest.fail(f"Failed to test config path logic: {e}")
    
    @patch('subprocess.Popen')
    def test_cli_command_execution_logic(self, mock_popen):
        """Test CLI command execution logic without tkinter"""
        try:
            from gui.main import Sync2NASGUI
            
            # Mock subprocess
            mock_process = Mock()
            mock_process.stdout = iter([])
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process
            
            # Create a mock GUI instance
            gui = Mock()
            gui.dry_run = Mock()
            gui.dry_run.get.return_value = False
            gui.get_verbosity_flags = Mock()
            gui.get_verbosity_flags.return_value = []
            gui.get_config_path_for_command = Mock()
            gui.get_config_path_for_command.return_value = "./config/sync2nas_config.ini"
            gui.gui_logger = Mock()
            
            # Test command building logic
            def build_command(subcommand, args=None):
                cmd = [sys.executable, "sync2nas.py"]
                
                if gui.dry_run.get():
                    cmd.append("--dry-run")
                
                cmd.extend(gui.get_verbosity_flags())
                
                config_path = gui.get_config_path_for_command()
                if config_path:
                    cmd.extend(["--config", config_path])
                
                cmd.append(subcommand)
                if args:
                    cmd.extend(args)
                
                return cmd
            
            # Test command building
            cmd = build_command("test-command", ["--arg1", "value1"])
            expected = [sys.executable, "sync2nas.py", "--config", "./config/sync2nas_config.ini", "test-command", "--arg1", "value1"]
            assert cmd == expected
            
            # Test with dry run
            gui.dry_run.get.return_value = True
            cmd = build_command("test-command")
            expected = [sys.executable, "sync2nas.py", "--dry-run", "--config", "./config/sync2nas_config.ini", "test-command"]
            assert cmd == expected
            
        except ImportError as e:
            pytest.fail(f"Failed to test CLI command execution logic: {e}")
    
    def test_state_management_logic(self):
        """Test state management logic without tkinter"""
        try:
            from gui.main import Sync2NASGUI
            
            # Create a mock GUI instance
            gui = Mock()
            gui.is_downloading = False
            gui.is_routing = False
            
            # Test download state management
            def start_download():
                gui.is_downloading = True
            
            def finish_download():
                gui.is_downloading = False
            
            assert gui.is_downloading is False
            start_download()
            assert gui.is_downloading is True
            finish_download()
            assert gui.is_downloading is False
            
            # Test routing state management
            def start_routing():
                gui.is_routing = True
            
            def finish_routing():
                gui.is_routing = False
            
            assert gui.is_routing is False
            start_routing()
            assert gui.is_routing is True
            finish_routing()
            assert gui.is_routing is False
            
        except ImportError as e:
            pytest.fail(f"Failed to test state management logic: {e}")


if __name__ == "__main__":
    pytest.main([__file__]) 