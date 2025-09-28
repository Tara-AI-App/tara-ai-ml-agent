"""
Source manager for orchestrating content discovery across different sources.
"""
from typing import List, Dict, Any, Optional
from ..tools import SourceResult, SearchQuery, SourceType
from ..tools.rag_tool import RAGTool
from ..tools.github_tool import GitHubMCPTool
from ..tools.search_tool import GoogleSearchTool
from ..config.settings import settings, SourcePriority
from ..utils.logger import logger


class SourceManager:
    """Manages content discovery across different sources."""

    def __init__(self):
        self.rag_tool = RAGTool()
        self.github_tool = GitHubMCPTool()
        self.search_tool = GoogleSearchTool()
        self._source_priority = settings.source_priority

    async def discover_content(self, topic: str) -> Dict[str, List[SourceResult]]:
        """
        Discover content for a topic using the configured priority strategy.

        Returns:
            Dict with keys: 'rag_results', 'github_results', 'used_sources'
        """
        logger.info(f"Starting content discovery for topic: {topic}")

        # Initialize results
        rag_results: List[SourceResult] = []
        github_results: List[SourceResult] = []
        search_results: List[SourceResult] = []
        used_sources: List[str] = []

        if self._source_priority == SourcePriority.RAG_FIRST:
            rag_results, github_results, used_sources = await self._rag_first_strategy(topic)
        elif self._source_priority == SourcePriority.GITHUB_FIRST:
            github_results, rag_results, used_sources = await self._github_first_strategy(topic)
        else:  # BALANCED
            rag_results, github_results, used_sources = await self._balanced_strategy(topic)

        # Fallback to Google Search if insufficient results from primary sources
        total_primary_results = len(rag_results) + len(github_results)
        if total_primary_results < 3:  # Minimum threshold for sufficient content
            logger.info("Insufficient results from primary sources, falling back to Google Search")
            search_results = await self._search_web(topic)
            if search_results:
                used_sources.append("Google Search")

        logger.info(f"Content discovery completed. Sources used: {used_sources}")

        return {
            'rag_results': rag_results,
            'github_results': github_results,
            'search_results': search_results,
            'used_sources': used_sources,
            'total_results': len(rag_results) + len(github_results) + len(search_results)
        }

    async def _rag_first_strategy(self, topic: str) -> tuple[List[SourceResult], List[SourceResult], List[str]]:
        """RAG-first content discovery strategy."""
        rag_results = []
        github_results = []
        used_sources = []

        # 1. Try RAG first
        if self.rag_tool.is_available():
            try:
                query = SearchQuery(query=topic, max_results=settings.rag.max_results)
                rag_results = await self.rag_tool.search(query)
                used_sources.append("RAG")

                # Check if RAG results are sufficient
                if self.rag_tool.assess_content_sufficiency(rag_results, topic):
                    logger.info("RAG results sufficient - skipping GitHub search")
                    return rag_results, github_results, used_sources

            except Exception as e:
                logger.warning(f"RAG search failed: {e}")

        # 2. Supplement with GitHub if needed
        github_results = await self._search_github(topic)
        if github_results:
            used_sources.append("GitHub")

        return rag_results, github_results, used_sources

    async def _github_first_strategy(self, topic: str) -> tuple[List[SourceResult], List[SourceResult], List[str]]:
        """GitHub-first content discovery strategy."""
        github_results = []
        rag_results = []
        used_sources = []

        # 1. Try GitHub first
        github_results = await self._search_github(topic)
        if github_results:
            used_sources.append("GitHub")

        # 2. Supplement with RAG
        if self.rag_tool.is_available():
            try:
                query = SearchQuery(query=topic, max_results=settings.rag.max_results)
                rag_results = await self.rag_tool.search(query)
                if rag_results:
                    used_sources.append("RAG")
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")

        return rag_results, github_results, used_sources

    async def _balanced_strategy(self, topic: str) -> tuple[List[SourceResult], List[SourceResult], List[str]]:
        """Balanced content discovery strategy."""
        rag_results = []
        github_results = []
        used_sources = []

        # Search both sources concurrently (conceptually)
        if self.rag_tool.is_available():
            try:
                query = SearchQuery(query=topic, max_results=settings.rag.max_results // 2)
                rag_results = await self.rag_tool.search(query)
                if rag_results:
                    used_sources.append("RAG")
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")

        github_results = await self._search_github(topic)
        if github_results:
            used_sources.append("GitHub")

        return rag_results, github_results, used_sources

    async def _search_github(self, topic: str) -> List[SourceResult]:
        """Search GitHub repositories for the topic."""
        if not self.github_tool.is_available():
            logger.warning("GitHub tools not available")
            return []

        try:
            # Search for repositories
            repositories = await self.github_tool.search_repositories(
                query=topic,
                max_results=settings.mcp.max_repositories
            )

            # Convert to SourceResult format
            github_results = self.github_tool.extract_source_results(repositories)

            logger.info(f"Found {len(github_results)} GitHub repositories for topic: {topic}")
            return github_results

        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            return []

    async def get_repository_content(self, repository: str, file_patterns: List[str]) -> Dict[str, str]:
        """Get specific file contents from a repository."""
        if not self.github_tool.is_available():
            return {}

        content = {}
        for pattern in file_patterns:
            try:
                file_content = await self.github_tool.get_file_contents(repository, pattern)
                content[pattern] = file_content
            except Exception as e:
                logger.warning(f"Failed to get {pattern} from {repository}: {e}")

        return content

    async def search_code_in_repositories(self, query: str, repositories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for specific code patterns across repositories."""
        if not self.github_tool.is_available():
            return []

        all_results = []
        if repositories:
            for repo in repositories:
                try:
                    results = await self.github_tool.search_code(query, repo)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Code search failed in {repo}: {e}")
        else:
            try:
                results = await self.github_tool.search_code(query)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Global code search failed: {e}")

        return all_results

    async def _search_web(self, topic: str) -> List[SourceResult]:
        """Search web for the topic as a fallback."""
        if not self.search_tool.is_available():
            logger.warning("Google Search tools not available")
            return []

        try:
            # Search for web content
            query = SearchQuery(query=topic, max_results=settings.mcp.max_repositories)
            search_results = await self.search_tool.search(query)

            logger.info(f"Found {len(search_results)} web search results for topic: {topic}")
            return search_results

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []