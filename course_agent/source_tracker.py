"""
Source tracking utilities for traceability
"""
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class SourceReference:
    """Single source reference"""
    source_type: str  # 'rag', 'mcp', 'search'
    content: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    relevance_score: Optional[float] = None
    line_range: Optional[str] = None
    repository: Optional[str] = None
    concepts: List[str] = None
    
    def __post_init__(self):
        if self.concepts is None:
            self.concepts = []

class SourceTracker:
    """Centralized source tracking"""
    
    def __init__(self, max_references_per_type: int = 5):
        self.max_references_per_type = max_references_per_type
        self.rag_sources: List[SourceReference] = []
        self.mcp_sources: List[SourceReference] = []
        self.search_sources: List[SourceReference] = []
        
    def add_rag_source(self, content: str, file_path: Optional[str] = None, 
                      relevance_score: Optional[float] = None, concepts: Optional[List[str]] = None) -> None:
        """Add RAG source reference"""
        if len(self.rag_sources) >= self.max_references_per_type:
            return
            
        source = SourceReference(
            source_type='rag',
            content=content,
            file_path=file_path,
            relevance_score=relevance_score,
            concepts=concepts or []
        )
        self.rag_sources.append(source)
        
    def add_mcp_source(self, content: str, file_path: Optional[str] = None, 
                      repository: Optional[str] = None, url: Optional[str] = None,
                      line_range: Optional[str] = None, concepts: Optional[List[str]] = None) -> None:
        """Add MCP source reference"""
        if len(self.mcp_sources) >= self.max_references_per_type:
            return
            
        source = SourceReference(
            source_type='mcp',
            content=content,
            file_path=file_path,
            repository=repository,
            url=url,
            line_range=line_range,
            concepts=concepts or []
        )
        self.mcp_sources.append(source)
        
    def add_search_source(self, content: str, url: Optional[str] = None,
                         relevance_score: Optional[float] = None, concepts: Optional[List[str]] = None) -> None:
        """Add search source reference"""
        if len(self.search_sources) >= self.max_references_per_type:
            return
            
        source = SourceReference(
            source_type='search',
            content=content,
            url=url,
            relevance_score=relevance_score,
            concepts=concepts or []
        )
        self.search_sources.append(source)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get source tracking summary"""
        return {
            "source_summary": {
                "total_sources": len(self.rag_sources) + len(self.mcp_sources) + len(self.search_sources),
                "rag_sources_count": len(self.rag_sources),
                "mcp_sources_count": len(self.mcp_sources),
                "search_sources_count": len(self.search_sources),
                "timestamp": datetime.now().isoformat()
            },
            "source_references": {
                "rag_sources": [
                    {
                        "file_path": src.file_path,
                        "relevance_score": src.relevance_score,
                        "concepts": src.concepts,
                        "content_preview": src.content[:200] + "..." if len(src.content) > 200 else src.content
                    }
                    for src in self.rag_sources
                ],
                "mcp_sources": [
                    {
                        "file_path": src.file_path,
                        "repository": src.repository,
                        "url": src.url,
                        "line_range": src.line_range,
                        "concepts": src.concepts,
                        "content_preview": src.content[:200] + "..." if len(src.content) > 200 else src.content
                    }
                    for src in self.mcp_sources
                ],
                "search_sources": [
                    {
                        "url": src.url,
                        "relevance_score": src.relevance_score,
                        "concepts": src.concepts,
                        "content_preview": src.content[:200] + "..." if len(src.content) > 200 else src.content
                    }
                    for src in self.search_sources
                ]
            }
        }