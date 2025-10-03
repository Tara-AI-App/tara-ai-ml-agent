"""
Google Search tool implementation for course content discovery.
"""
from typing import List, Dict, Any
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.runners import InMemoryRunner
from google.genai import types
import uuid

from .base import ContentSource, SourceResult, SourceType, SearchQuery
from ..config.settings import settings
from ..utils.logger import logger


class GoogleSearchTool(ContentSource):
    """Google Search tool for external content discovery."""

    def __init__(self):
        # Create specialized search agent for course content
        self.search_agent = Agent(
            model=settings.model_name,
            name="course_search_agent",
            instruction="""
            You are a specialist in finding educational and technical content using Google Search.
            Focus on finding:
            - Tutorial and educational content
            - Technical documentation
            - Code examples and implementations
            - Best practices and guides
            - Recent blog posts and articles

            When searching, prioritize:
            1. Official documentation
            2. Well-known educational platforms (Medium, Dev.to, etc.)
            3. Technical blogs from reputable sources
            4. Recent content (prefer newer articles)

            Return results with clear descriptions of their educational value.
            """,
            tools=[google_search],
        )

        # Create runner for executing the search agent
        self.runner = InMemoryRunner(agent=self.search_agent)

    async def search(self, query: SearchQuery) -> List[SourceResult]:
        """Search using Google Search for educational content."""
        try:
            logger.info(f"Searching Google for: {query.query}")

            # Enhance query for educational content
            enhanced_query = self._enhance_search_query(query.query)

            # Perform search using the search agent
            search_prompt = f"""
            Search for educational content about: {enhanced_query}

            Find {query.max_results} high-quality resources that would be useful for creating a technical course.
            Focus on tutorials, documentation, examples, and guides.
            """

            # Execute search through the runner
            search_results = await self._run_search_agent(search_prompt)

            # Parse and convert results to SourceResult format
            source_results = self._parse_search_results(search_results, query.query)

            logger.info(f"Found {len(source_results)} relevant search results")
            return source_results

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []

    async def _run_search_agent(self, prompt: str) -> str:
        """Run the search agent with the given prompt."""
        try:
            # Generate IDs
            user_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())

            # Create session
            await self.runner.session_service.create_session(
                user_id=user_id,
                session_id=session_id,
                app_name=self.runner.app_name
            )

            # Create user message
            new_message = types.Content(
                role="user",
                parts=[types.Part(text=prompt)]
            )

            # Run agent and collect response
            response_text = ""
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message
            ):
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text += part.text

            return response_text

        except Exception as e:
            logger.error(f"Search agent execution failed: {e}")
            return ""

    def _enhance_search_query(self, query: str) -> str:
        """Enhance search query for better educational content discovery."""
        # Add educational keywords
        educational_keywords = [
            "tutorial", "guide", "how to", "documentation",
            "example", "implementation", "best practices"
        ]

        # Add technical content indicators
        enhanced_query = f"{query} tutorial OR guide OR documentation OR example"

        # Add site restrictions for quality content
        quality_sites = [
            "site:medium.com", "site:dev.to", "site:github.com",
            "site:stackoverflow.com", "site:docs.python.org",
            "site:tensorflow.org", "site:pytorch.org"
        ]

        # Combine with OR for broader search
        site_restriction = " OR ".join(quality_sites)
        enhanced_query = f"({enhanced_query}) AND ({site_restriction})"

        return enhanced_query

    def _parse_search_results(self, search_results: str, original_query: str) -> List[SourceResult]:
        """Parse search agent results into SourceResult format."""
        source_results = []

        try:
            # Parse the search results (assuming they come as structured text)
            # This is a simplified parser - you may need to adjust based on actual output format
            lines = search_results.split('\n')

            current_result = {}
            for line in lines:
                line = line.strip()
                if not line:
                    if current_result and 'title' in current_result:
                        # Convert to SourceResult
                        source_result = SourceResult(
                            content=current_result.get('description', ''),
                            source_type=SourceType.SEARCH,
                            url=current_result.get('url', ''),
                            title=current_result.get('title', ''),
                            relevance_score=self._calculate_relevance(
                                current_result.get('description', ''),
                                original_query
                            ),
                            metadata={
                                'search_query': original_query,
                                'source': 'google_search',
                                'snippet': current_result.get('snippet', '')
                            }
                        )
                        source_results.append(source_result)
                        current_result = {}
                elif line.startswith('Title:'):
                    current_result['title'] = line.replace('Title:', '').strip()
                elif line.startswith('URL:'):
                    current_result['url'] = line.replace('URL:', '').strip()
                elif line.startswith('Description:'):
                    current_result['description'] = line.replace('Description:', '').strip()
                elif line.startswith('Snippet:'):
                    current_result['snippet'] = line.replace('Snippet:', '').strip()

            # Don't forget the last result
            if current_result and 'title' in current_result:
                source_result = SourceResult(
                    content=current_result.get('description', ''),
                    source_type=SourceType.WEB_SEARCH,
                    url=current_result.get('url', ''),
                    title=current_result.get('title', ''),
                    relevance_score=self._calculate_relevance(
                        current_result.get('description', ''),
                        original_query
                    ),
                    metadata={
                        'search_query': original_query,
                        'source': 'google_search',
                        'snippet': current_result.get('snippet', '')
                    }
                )
                source_results.append(source_result)

        except Exception as e:
            logger.warning(f"Failed to parse search results: {e}")
            # Fallback: create a single result with the raw search output
            source_results = [SourceResult(
                content=search_results,
                source_type=SourceType.WEB_SEARCH,
                url="",
                title="Google Search Results",
                relevance_score=0.5,
                metadata={
                    'search_query': original_query,
                    'source': 'google_search',
                    'raw_output': True
                }
            )]

        return source_results

    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score between content and query."""
        if not content or not query:
            return 0.0

        # Simple keyword matching relevance
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)

        if not union:
            return 0.0

        # Jaccard similarity
        relevance = len(intersection) / len(union)

        # Boost for educational keywords
        educational_keywords = ['tutorial', 'guide', 'documentation', 'example', 'how']
        if any(keyword in content.lower() for keyword in educational_keywords):
            relevance += 0.2

        return min(relevance, 1.0)

    def is_available(self) -> bool:
        """Check if Google Search is available."""
        return True  # Google Search tool should always be available

    def get_source_type(self) -> SourceType:
        """Get source type."""
        return SourceType.SEARCH

    def assess_content_sufficiency(self, results: List[SourceResult], topic: str) -> bool:
        """Assess if search results are sufficient for course generation."""
        if not results:
            return False

        # Check for minimum number of quality results
        quality_results = [
            r for r in results
            if r.relevance_score and r.relevance_score >= 0.5
        ]

        # Need at least 2 quality results for basic course content
        return len(quality_results) >= 2