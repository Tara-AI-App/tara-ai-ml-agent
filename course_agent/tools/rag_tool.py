"""
RAG tool implementation for internal knowledge retrieval.
"""
from typing import List, Dict, Any
from .base import ContentSource, SourceResult, SourceType, SearchQuery
from ..config.settings import settings
from ..utils.logger import logger
from ..utils.cache import cached_search
from ..rag_processor import rag_integration


class RAGTool(ContentSource):
    """RAG tool for searching internal knowledge base."""

    def __init__(self):
        self.rag_processor = rag_integration

    @cached_search
    async def search(self, query: SearchQuery) -> List[SourceResult]:
        """Search internal RAG knowledge base with caching."""
        try:
            logger.info(f"Searching RAG for: {query.query}")

            results = self.rag_processor.get_code_examples(
                query.query,
                top_n=min(query.max_results, settings.rag.max_results)
            )

            if not results:
                logger.warning(f"No RAG results found for query: {query.query}")
                return []

            source_results = []
            for result in results:
                if not result.get("error"):
                    # Filter by relevance if threshold is set
                    relevance_score = result.get("relevance_score")
                    if (relevance_score is not None and
                        relevance_score < settings.rag.relevance_threshold):
                        continue

                    source_result = SourceResult(
                        content=result.get("code_snippet", ""),
                        source_type=SourceType.RAG,
                        file_path=result.get("file_path", ""),
                        relevance_score=relevance_score,
                        metadata={
                            "key_concepts": result.get("key_concepts", []),
                            "context": result.get("context", ""),
                        }
                    )
                    source_results.append(source_result)

            logger.info(f"Found {len(source_results)} relevant RAG results")
            return source_results

        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            raise

    def is_available(self) -> bool:
        """Check if RAG is available."""
        try:
            return self.rag_processor is not None
        except Exception:
            return False

    def get_source_type(self) -> SourceType:
        """Get source type."""
        return SourceType.RAG

    def assess_content_sufficiency(self, results: List[SourceResult], topic: str) -> bool:
        """Assess if RAG results are sufficient for course generation."""
        if not results:
            return False

        # Check if we have enough high-quality results
        high_quality_results = [
            r for r in results
            if r.relevance_score and r.relevance_score >= settings.rag.relevance_threshold
        ]

        # Need at least 3 high-quality results with substantial content
        if len(high_quality_results) < 3:
            return False

        # Check content depth
        total_content_length = sum(len(r.content) for r in high_quality_results)
        if total_content_length < 1000:  # Minimum content threshold
            return False

        logger.info(f"RAG content assessment: {len(high_quality_results)} quality results, {total_content_length} chars")
        return True