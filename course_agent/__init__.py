"""
Course Generator Agent Package
Following Google ADK structure
"""

from .agent import root_agent, interactive_course_agent
from .config import config

__all__ = ["root_agent", "interactive_course_agent", "config"]