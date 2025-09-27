"""
Course Generator Agent Package with Source Tracking
"""

from .agent import course_generator, root_agent
from .config import config
from .source_tracker import SourceTracker

__all__ = ["course_generator", "root_agent", "config", "SourceTracker"]