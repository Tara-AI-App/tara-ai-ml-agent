"""
Centralized logging system for course agent.
"""
import logging
import sys
from typing import Optional
from ..config.settings import settings


class CourseAgentLogger:
    """Centralized logger for the course agent."""

    _instance: Optional['CourseAgentLogger'] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> 'CourseAgentLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        """Setup the logger with appropriate configuration."""
        self._logger = logging.getLogger('course_agent')
        self._logger.setLevel(getattr(logging, settings.log_level.value))

        # Remove existing handlers to avoid duplicates
        self._logger.handlers.clear()

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.log_level.value))

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        console_handler.setFormatter(formatter)

        # Add handler to logger
        self._logger.addHandler(console_handler)

        # Prevent propagation to root logger
        self._logger.propagate = False

        # Suppress ADK warnings
        logging.getLogger('google_adk.google.adk.tools.base_authenticated_tool').setLevel(logging.ERROR)
        logging.getLogger('google.adk').setLevel(logging.ERROR)
        logging.getLogger('google_adk').setLevel(logging.ERROR)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._logger.error(message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, **kwargs)


# Global logger instance
logger = CourseAgentLogger()