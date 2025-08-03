#!/usr/bin/env python3
"""
Sync2NAS Enhanced GUI Launcher
Launches the enhanced GUI with ttkbootstrap styling.
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main import main

if __name__ == "__main__":
    main() 