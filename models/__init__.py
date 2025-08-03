"""
Models package for Sync2NAS.

This package contains Pydantic-based models for TV shows and episodes.
"""

from .show import Show
from .episode import Episode

__all__ = ["Show", "Episode"]
