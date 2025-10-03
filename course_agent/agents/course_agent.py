"""
Refactored course generation agent with modular architecture.
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# Apply JSON encoder patch early to handle Pydantic serialization issues
from ..utils.json_encoder import CustomJSONEncoder

# Monkey patch json.dumps globally
_original_dumps = json.dumps
def patched_dumps(obj, **kwargs):
    if 'cls' not in kwargs:
        kwargs['cls'] = CustomJSONEncoder
    return _original_dumps(obj, **kwargs)

json.dumps = patched_dumps

from ..config.settings import settings
from ..utils.logger import logger
from ..core.source_manager import SourceManager
from ..core.enhanced_source_tracker import EnhancedSourceTracker


class CourseGenerationAgent:
    """Main course generation agent with modular architecture."""

    def __init__(self, github_token: str = None, drive_token: str = None):
        """
        Initialize the course generation agent.

        Args:
            github_token: GitHub personal access token (overrides env var)
            drive_token: Google Drive token (for future use)
        """
        # Set tokens in environment if provided
        if github_token:
            os.environ['GITHUB_PERSONAL_ACCESS_TOKEN'] = github_token
        if drive_token:
            os.environ['GOOGLE_DRIVE_TOKEN'] = drive_token

        self.settings = settings
        self.source_manager = SourceManager()
        self.source_tracker = EnhancedSourceTracker()
        self.agent = self._create_agent()

        # Validate configuration
        config_issues = self.settings.validate()
        if config_issues:
            logger.warning(f"Configuration issues detected: {config_issues}")

    def _create_agent(self) -> Agent:
        """Create the ADK agent with proper configuration."""
        tools = [
            FunctionTool(self.analyze_tech_stack),
            FunctionTool(self.discover_sources),
            FunctionTool(self.extract_repository_content),
            FunctionTool(self.get_tracked_sources),
            FunctionTool(self.determine_difficulty),
            FunctionTool(self.generate_search_queries),
            FunctionTool(self.save_course_to_file)
        ]

        # Add MCP tools if available
        logger.info(f"Checking if GitHub MCP tools are available...")
        github_available = self.source_manager.github_tool.is_available()
        logger.info(f"GitHub tool is_available(): {github_available}")

        if github_available:
            # Add the MCP toolset with JSON encoder patch applied
            mcp_toolset = self.source_manager.github_tool._mcp_tools
            logger.info(f"Retrieved MCP toolset: {mcp_toolset}")
            logger.info(f"MCP toolset type: {type(mcp_toolset)}")

            if mcp_toolset:
                tools.append(mcp_toolset)
                logger.info("GitHub MCP toolset added to agent (with JSON encoder patch)")
                logger.info(f"Total tools count: {len(tools)}")
            else:
                logger.warning("GitHub MCP toolset is None")
        else:
            logger.warning("GitHub MCP tools not available")

        return Agent(
            model=self.settings.model_name,
            name=self.settings.name,
            description=self.settings.description,
            instruction=self._get_agent_instruction(),
            tools=tools
        )

    def _get_agent_instruction(self) -> str:
        """Get comprehensive agent instruction."""
        return f"""
        You are an expert course generator that creates technical courses using dynamic source discovery.

        **CONFIGURATION:**
        - Source Priority: {self.settings.source_priority.value}
        - Max Repositories: {self.settings.mcp.max_repositories}
        - RAG Max Results: {self.settings.rag.max_results}
        - GitHub Tools Available: {self.source_manager.github_tool.is_available()}

        **CONTENT DISCOVERY PROCESS:**
        1. Use analyze_tech_stack to understand the topic complexity and requirements
        2. **PRIORITY: Use RAG tool first** with discover_sources to find relevant internal context
           - RAG tool will search internal knowledge base and documentation
           - If RAG finds sufficient relevant context, prioritize this content for course generation
        3. **FALLBACK: If no relevant RAG context found**, then use GitHub MCP tools:
           - Use list_projects to find relevant internal/organizational projects
           - Use search_repositories with multiple related terms (e.g., for "LGBM GCP" try: "lightgbm", "machine learning gcp", "gradient boosting", "ml deployment")
           - Use search_code to find specific implementation patterns
        4. Use get_file_contents to extract actual code examples from discovered repositories
        5. Use get_tracked_sources to retrieve all discovered source URLs for inclusion

        **RAG TOOL (PRIORITY TOOL):**
        - discover_sources: Search internal knowledge base and documentation for relevant context

        **GITHUB MCP TOOLS AVAILABLE (FALLBACK TOOLS):**
        - list_projects: List internal/organizational projects
        - search_repositories: Find repositories by name, description, topics
        - search_code: Search for specific code patterns across GitHub
        - get_file_contents: Extract actual files from repositories

        **GOOGLE SEARCH TOOL (FINAL FALLBACK):**
        - Automatically triggered when RAG and GitHub MCP provide insufficient results (< 3 total)
        - Searches for educational content, tutorials, documentation, and guides
        - Focuses on high-quality sources from reputable educational platforms


        **DYNAMIC CONTENT EXTRACTION:**
        - Extract real code snippets from discovered repositories using get_file_contents
        - Reference actual file paths and repository locations
        - Build course structure based on real-world examples found via search_code
        - Include direct links to repository files for hands-on learning

        **SEARCH STRATEGY FOR DIFFICULT TOPICS:**
        If no relevant RAG context and no external repositories found for exact topic (e.g., "machine learning deployment using LGBM in GCP"):
        1. First, retry discover_sources with generate_search_queries to get alternative search terms for RAG
        2. If RAG still yields no results, then use GitHub MCP tools:
           - Use search_repositories with each suggested query from generate_search_queries
           - Use search_code to find specific implementations with patterns like: "lightgbm train", "model deployment gcp", etc.
           - Use list_projects to check organizational repositories
        3. Use get_file_contents to extract actual code from found repositories
        4. **FINAL FALLBACK**: If combined RAG + GitHub results < 3, Google Search automatically activates:
           - Searches for educational content, tutorials, and documentation
           - Prioritizes official docs, educational platforms, and recent articles
           - Provides web-based learning resources as course references
        5. Combine results from all sources to create comprehensive course content

        **IMPORTANT**:
        - Always prioritize RAG tool (internal context) first using discover_sources
        - Use GitHub MCP tools only as fallback when RAG doesn't provide relevant context
        - Never give up if first search fails. Always use generate_search_queries and try multiple approaches
        - Always prefer internal RAG context over external GitHub sources when available

        **COURSE GENERATION REQUIREMENTS:**
        - Use only discovered content - NO templates or fallbacks
        - Include actual code from real repositories with proper attribution
        - Structure content based on complexity progression found in examples
        - Reference specific file paths: repository/path/to/file.py
        - Include repository URLs in source_from array
        - Estimated duration: {self.settings.course.default_duration}
        - Default difficulty: {self.settings.course.default_difficulty}

        **OUTPUT FORMAT:**
        Generate a comprehensive course in JSON format with:
        {{
            "title": "Descriptive Course Title",
            "description": "Course overview based on discovered content",
            "difficulty": "Beginner|Intermediate|Advanced",
            "estimated_duration": 10,
            "learning_objectives": ["objective1", "objective2", ...],
            "skills": ["skill1", "skill2", "skill3", ...],
            "modules": [
                {{
                    "title": "Module Title",
                    "index": 1,
                    "lessons": [
                        {{
                            "title": "Lesson Title",
                            "index": 1,
                            "content": "# Lesson Title\\n\\n## Real Example\\n\\nFrom: https://github.com/owner/repo/blob/main/path/file.py\\n\\n```language\\n// Actual code from repository\\nreal_code_here()\\n```\\n\\n**Explanation**: This code from [repository name] demonstrates..."
                        }}
                    ],
                    "quiz": [
                        {{
                            "question": "What is the main purpose of...?",
                            "choices": {{
                                "A": "First option",
                                "B": "Second option",
                                "C": "Third option",
                                "D": "Fourth option (optional)"
                            }},
                            "answer": "B"
                        }}
                    ]
                }}
            ],
            "source_from": ["https://github.com/owner/repo", "internal/path.md"]
        }}

        **QUIZ REQUIREMENTS:**
        - Each module must have 2-4 quiz questions
        - Quiz questions should test understanding of key concepts from the module
        - Provide 3-4 answer choices (A, B, C, and optionally D)
        - Mark the correct answer with the letter (A/B/C/D)
        - Make questions specific to the content, not generic

        **SKILLS EXTRACTION:**
        - Extract 8-12 relevant skills from the course content
        - Include technologies, frameworks, platforms, and concepts
        - List both broad skills (e.g., "Machine Learning") and specific ones (e.g., "XGBoost", "Vertex AI")
        - Skills should reflect what learners will gain from the course

        CRITICAL: All code examples must be real code from discovered repositories with proper attribution.
        """

    def analyze_tech_stack(self, topic: str) -> Dict[str, Any]:
        """Analyze technology stack and complexity for the topic."""
        logger.info(f"Analyzing tech stack for topic: {topic}")

        words = topic.lower().split()

        # Enhanced technology categorization
        tech_categories = {
            "machine_learning": ["ml", "machine", "learning", "ai", "tensorflow", "pytorch", "xgboost", "sklearn", "merlin"],
            "cloud_computing": ["cloud", "aws", "gcp", "azure", "kubernetes", "docker", "serverless"],
            "web_development": ["web", "react", "vue", "angular", "flask", "django", "fastapi", "node"],
            "data_engineering": ["data", "pipeline", "etl", "spark", "airflow", "kafka"],
            "devops": ["devops", "ci", "cd", "jenkins", "github", "actions", "deployment"]
        }

        # Determine primary category
        category = "software_development"  # default
        for cat, keywords in tech_categories.items():
            if any(word in words for word in keywords):
                category = cat
                break

        # Determine complexity based on topic keywords
        complexity_indicators = {
            "advanced": ["production", "scaling", "distributed", "optimization", "mlops", "enterprise"],
            "beginner": ["introduction", "basics", "getting", "started", "tutorial", "hello", "simple"],
            "intermediate": ["deployment", "implementation", "building", "creating"]
        }

        complexity = self.settings.course.default_difficulty.lower()
        for level, indicators in complexity_indicators.items():
            if any(indicator in topic.lower() for indicator in indicators):
                complexity = level.capitalize()
                break

        result = {
            "primary_technology": words[0] if words else "unknown",
            "category": category,
            "complexity": complexity,
            "related_technologies": words[1:],
            "recommended_duration": self.settings.course.default_duration,
            "analysis_timestamp": datetime.now().isoformat()
        }

        logger.info(f"Tech stack analysis complete: {category} - {complexity}")
        return result

    async def discover_sources(self, topic: str) -> Dict[str, Any]:
        """Discover content sources for the topic."""
        logger.info(f"Starting content discovery for: {topic}")

        try:
            discovery_result = await self.source_manager.discover_content(topic)

            # Track discovered sources
            for source_result in discovery_result['rag_results']:
                self.source_tracker.add_source_result(source_result)

            for source_result in discovery_result['github_results']:
                self.source_tracker.add_source_result(source_result)

            for source_result in discovery_result.get('search_results', []):
                self.source_tracker.add_source_result(source_result)

            # Validate source quality
            validation_issues = self.source_tracker.validate_sources()
            if validation_issues:
                logger.warning(f"Source validation issues: {validation_issues}")

            return {
                "total_sources_found": discovery_result['total_results'],
                "sources_used": discovery_result['used_sources'],
                "rag_results_count": len(discovery_result['rag_results']),
                "github_results_count": len(discovery_result['github_results']),
                "search_results_count": len(discovery_result.get('search_results', [])),
                "discovery_strategy": self.settings.source_priority.value,
                "validation_issues": validation_issues
            }

        except Exception as e:
            logger.error(f"Content discovery failed: {e}")
            raise

    async def extract_repository_content(self, repository: str, file_patterns: List[str]) -> Dict[str, str]:
        """Extract specific content from a repository."""
        logger.info(f"Extracting content from repository: {repository}")

        try:
            content = await self.source_manager.get_repository_content(repository, file_patterns)
            logger.info(f"Extracted {len(content)} files from {repository}")
            return content
        except Exception as e:
            logger.error(f"Repository content extraction failed: {e}")
            return {}

    def get_tracked_sources(self) -> List[str]:
        """Get all tracked source URLs and paths."""
        return self.source_tracker.get_source_urls()

    def determine_difficulty(self, topic: str) -> str:
        """Determine course difficulty based on topic analysis."""
        analysis = self.analyze_tech_stack(topic)
        return analysis.get("complexity", self.settings.course.default_difficulty)

    def generate_search_queries(self, topic: str) -> Dict[str, Any]:
        """Generate multiple search queries for better repository discovery."""
        topic_lower = topic.lower()

        # Base queries
        queries = [topic]

        # Component extraction
        components = []

        # ML frameworks
        ml_frameworks = ["lgbm", "lightgbm", "xgboost", "tensorflow", "pytorch", "sklearn"]
        for framework in ml_frameworks:
            if framework in topic_lower:
                components.append(framework)
                queries.append(f"{framework} tutorial")
                queries.append(f"{framework} deployment")

        # Cloud platforms
        cloud_platforms = ["gcp", "google cloud", "aws", "azure"]
        for platform in cloud_platforms:
            if platform in topic_lower or platform.replace(" ", "") in topic_lower:
                components.append(platform)
                queries.append(f"machine learning {platform}")
                queries.append(f"ml deployment {platform}")

        # ML concepts
        ml_concepts = ["deployment", "machine learning", "model", "training"]
        for concept in ml_concepts:
            if concept in topic_lower:
                components.append(concept)

        # Generate combination queries
        if len(components) >= 2:
            queries.append(f"{components[0]} {components[1]}")

        # Add general fallbacks
        queries.extend([
            "machine learning deployment",
            "ml model deployment",
            "mlops tutorial"
        ])

        return {
            "original_topic": topic,
            "search_queries": list(set(queries[:8])),  # Remove duplicates, limit to 8
            "components_found": components,
            "strategy": "multi_query_approach"
        }


    def save_course_to_file(self, course_content: Dict[str, Any], filename: str) -> Dict[str, str]:
        """Save course with enhanced validation and tracking."""
        logger.info(f"Saving course to file: {filename}")

        # Validate required fields
        required_fields = ["title", "description", "modules"]
        missing_fields = [field for field in required_fields if not course_content.get(field)]
        if missing_fields:
            raise ValueError(f"Course content missing required fields: {missing_fields}")

        # Add enhanced tracking information
        course_content["source_tracking"] = self.source_tracker.get_summary()
        course_content["source_from"] = self.get_tracked_sources()

        # Add generation metadata
        course_content["generation_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "agent_version": "2.0.0",
            "configuration": {
                "source_priority": self.settings.source_priority.value,
                "github_enabled": self.source_manager.github_tool.is_available(),
                "rag_enabled": self.source_manager.rag_tool.is_available()
            }
        }

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)

            # Save course with proper formatting
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(course_content, f, indent=2, ensure_ascii=False)

            logger.info(f"Course saved successfully: {filename}")
            return {"status": "success", "filename": filename, "sources_tracked": len(self.get_tracked_sources())}

        except Exception as e:
            logger.error(f"Failed to save course: {e}")
            raise



    def get_agent(self) -> Agent:
        """Get the configured ADK agent."""
        return self.agent

    def get_configuration_status(self) -> Dict[str, Any]:
        """Get comprehensive configuration and status information."""
        return {
            "agent_name": self.settings.name,
            "source_priority": self.settings.source_priority.value,
            "github_available": self.source_manager.github_tool.is_available(),
            "rag_available": self.source_manager.rag_tool.is_available(),
            "configuration_issues": self.settings.validate(),
            "max_repositories": self.settings.mcp.max_repositories,
            "max_rag_results": self.settings.rag.max_results,
            "log_level": self.settings.log_level.value
        }


# Create the main agent instance
def create_course_agent(github_token: str = None, drive_token: str = None) -> CourseGenerationAgent:
    """
    Factory function to create a configured course generation agent.

    Args:
        github_token: GitHub personal access token (overrides env var)
        drive_token: Google Drive token (for future use)
    """
    agent = CourseGenerationAgent(github_token=github_token, drive_token=drive_token)
    logger.info(f"Course generation agent created: {agent.get_configuration_status()}")
    return agent