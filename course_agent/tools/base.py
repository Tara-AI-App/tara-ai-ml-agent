"""
Base classes and interfaces for course agent tools.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class SourceType(str, Enum):
    """Types of content sources."""
    RAG = "rag"
    GITHUB = "github"
    DOCUMENTATION = "documentation"
    SEARCH = "search"


@dataclass
class SourceResult:
    """Standardized result from any source."""
    content: str
    source_type: SourceType
    url: Optional[str] = None
    file_path: Optional[str] = None
    repository: Optional[str] = None
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchQuery:
    """Standardized search query."""
    query: str
    max_results: int = 5
    filters: Optional[Dict[str, Any]] = None


class ContentSource(ABC):
    """Abstract base class for content sources."""

    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SourceResult]:
        """Search for content based on query."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is available/configured."""
        pass

    @abstractmethod
    def get_source_type(self) -> SourceType:
        """Get the type of this source."""
        pass


class RepositoryTool(ABC):
    """Abstract base class for repository-related tools."""

    @abstractmethod
    async def search_repositories(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for repositories."""
        pass

    @abstractmethod
    async def get_file_contents(self, repository: str, file_path: str) -> str:
        """Get contents of a specific file."""
        pass

    @abstractmethod
    async def search_code(self, query: str, repository: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for code patterns."""
        pass


class CourseGenerator(ABC):
    """Abstract base class for course generation."""

    @abstractmethod
    async def generate_course(self, topic: str) -> Dict[str, Any]:
        """Generate a complete course for the given topic."""
        pass

    @abstractmethod
    def analyze_topic(self, topic: str) -> Dict[str, Any]:
        """Analyze the topic to determine tech stack and complexity."""
        pass


class SourceTracker(ABC):
    """Abstract base class for source tracking."""

    @abstractmethod
    def add_source(self, source_result: SourceResult):
        """Add a source to tracking."""
        pass

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all tracked sources."""
        pass

    @abstractmethod
    def get_source_urls(self) -> List[str]:
        """Get all source URLs."""
        pass