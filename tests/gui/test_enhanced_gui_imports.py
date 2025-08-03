"""
Test that the main GUI imports correctly and can be instantiated.
"""

import pytest
import tkinter as tk
import sys
import os

# Add the parent directory to the path so we can import from the main project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_gui_import():
    """Test that the main GUI can be imported"""
    try:
        from gui.main import Sync2NASGUI
        assert Sync2NASGUI is not None
    except ImportError as e:
        pytest.fail(f"Failed to import main GUI: {e}")


def test_gui_instantiation():
    """Test that the main GUI can be instantiated"""
    try:
        from gui.main import Sync2NASGUI
        
        # Create a temporary root window
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Create the GUI instance
        gui = Sync2NASGUI(root)
        
        # Verify the GUI was created
        assert gui is not None
        assert hasattr(gui, 'root')
        assert hasattr(gui, 'config_path')
        assert hasattr(gui, 'dry_run')
        assert hasattr(gui, 'verbose_level_str')
        
        # Clean up
        root.destroy()
        
    except Exception as e:
        pytest.fail(f"Failed to instantiate main GUI: {e}")


def test_gui_ttkbootstrap_availability():
    """Test that ttkbootstrap availability is detected correctly"""
    try:
        from gui.main import TTKBOOTSTRAP_AVAILABLE
        assert isinstance(TTKBOOTSTRAP_AVAILABLE, bool)
    except ImportError as e:
        pytest.fail(f"Failed to import TTKBOOTSTRAP_AVAILABLE: {e}")


if __name__ == "__main__":
    pytest.main([__file__]) 