"""
Enhanced source tracker with better organization and validation.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from ..tools.base import SourceResult, SourceType
from ..config.settings import settings
from ..utils.logger import logger


@dataclass
class TrackedSource:
    """Represents a tracked source with metadata."""
    content: str
    source_type: SourceType
    url: Optional[str] = None
    file_path: Optional[str] = None
    repository: Optional[str] = None
    relevance_score: Optional[float] = None
    concepts: List[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str = None

    def __post_init__(self):
        if self.concepts is None:
            self.concepts = []
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class EnhancedSourceTracker:
    """Enhanced source tracker with validation and better organization."""

    def __init__(self):
        self.sources: List[TrackedSource] = []
        self.max_sources_per_type = settings.source_tracking.max_references_per_type
        self.track_preview = settings.source_tracking.track_content_preview
        self.preview_length = settings.source_tracking.preview_length

    def add_source_result(self, source_result: SourceResult):
        """Add a SourceResult to tracking."""
        tracked_source = TrackedSource(
            content=self._get_content_preview(source_result.content),
            source_type=source_result.source_type,
            url=source_result.url,
            file_path=source_result.file_path,
            repository=source_result.repository,
            relevance_score=source_result.relevance_score,
            metadata=source_result.metadata or {}
        )

        self._add_tracked_source(tracked_source)

    def add_rag_source(self, content: str, file_path: str, relevance_score: Optional[float] = None, concepts: List[str] = None):
        """Add a RAG source (legacy compatibility)."""
        tracked_source = TrackedSource(
            content=self._get_content_preview(content),
            source_type=SourceType.RAG,
            file_path=file_path,
            relevance_score=relevance_score,
            concepts=concepts or []
        )
        self._add_tracked_source(tracked_source)

    def add_mcp_source(self, content: str, repository: str, url: str, concepts: List[str] = None):
        """Add an MCP/GitHub source (legacy compatibility)."""
        tracked_source = TrackedSource(
            content=self._get_content_preview(content),
            source_type=SourceType.GITHUB,
            url=url,
            repository=repository,
            concepts=concepts or []
        )
        self._add_tracked_source(tracked_source)

    def add_search_source(self, content: str, url: str, concepts: List[str] = None):
        """Add a search source (legacy compatibility)."""
        tracked_source = TrackedSource(
            content=self._get_content_preview(content),
            source_type=SourceType.SEARCH,
            url=url,
            concepts=concepts or []
        )
        self._add_tracked_source(tracked_source)

    def _add_tracked_source(self, tracked_source: TrackedSource):
        """Add a tracked source with type limits."""
        # Count existing sources of this type
        existing_count = len([s for s in self.sources if s.source_type == tracked_source.source_type])

        if existing_count >= self.max_sources_per_type:
            # Remove oldest source of this type
            oldest_index = next(
                i for i, s in enumerate(self.sources)
                if s.source_type == tracked_source.source_type
            )
            removed_source = self.sources.pop(oldest_index)
            logger.debug(f"Removed oldest {tracked_source.source_type} source: {removed_source.url or removed_source.file_path}")

        self.sources.append(tracked_source)
        logger.debug(f"Added {tracked_source.source_type} source: {tracked_source.url or tracked_source.file_path}")

    def _get_content_preview(self, content: str) -> str:
        """Get content preview based on settings."""
        if not self.track_preview:
            return ""

        if len(content) <= self.preview_length:
            return content

        return content[:self.preview_length] + "..."

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of tracked sources."""
        source_counts = {}
        for source_type in SourceType:
            source_counts[f"{source_type.value}_sources_count"] = len([
                s for s in self.sources if s.source_type == source_type
            ])

        return {
            "source_summary": {
                "total_sources": len(self.sources),
                **source_counts,
                "timestamp": datetime.now().isoformat()
            },
            "source_references": {
                f"{source_type.value}_sources": [
                    self._source_to_dict(s) for s in self.sources
                    if s.source_type == source_type
                ]
                for source_type in SourceType
            }
        }

    def get_source_urls(self) -> List[str]:
        """Get all source URLs and file paths."""
        urls = []

        for source in self.sources:
            if source.url and source.url not in urls:
                urls.append(source.url)
            elif source.file_path and source.file_path not in urls:
                urls.append(source.file_path)

        return urls

    def _source_to_dict(self, source: TrackedSource) -> Dict[str, Any]:
        """Convert TrackedSource to dictionary for serialization."""
        source_dict = asdict(source)

        # Add content preview if enabled
        if self.track_preview:
            source_dict["content_preview"] = source.content
        else:
            source_dict.pop("content", None)

        return source_dict

    def get_sources_by_type(self, source_type: SourceType) -> List[TrackedSource]:
        """Get all sources of a specific type."""
        return [s for s in self.sources if s.source_type == source_type]

    def get_high_relevance_sources(self, min_score: float = 0.7) -> List[TrackedSource]:
        """Get sources with high relevance scores."""
        return [
            s for s in self.sources
            if s.relevance_score and s.relevance_score >= min_score
        ]

    def validate_sources(self) -> Dict[str, List[str]]:
        """Validate tracked sources and return any issues."""
        issues = {
            "missing_urls": [],
            "low_quality": [],
            "duplicate_sources": []
        }

        seen_sources = set()
        for source in self.sources:
            # Check for missing URLs/paths
            if not source.url and not source.file_path:
                issues["missing_urls"].append(f"{source.source_type} source without URL or path")

            # Check for low quality (very short content)
            if len(source.content) < 10:
                issues["low_quality"].append(f"{source.source_type}: {source.url or source.file_path}")

            # Check for duplicates
            source_key = source.url or source.file_path
            if source_key:
                if source_key in seen_sources:
                    issues["duplicate_sources"].append(source_key)
                seen_sources.add(source_key)

        return issues