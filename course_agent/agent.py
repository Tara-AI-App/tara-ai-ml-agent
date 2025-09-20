import os
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
from datetime import datetime
from .config import config
from .sub_agents import (
    course_editor,
    robust_course_planner,
    robust_course_writer,
    robust_quiz_generator,
)
from .tools import analyze_tech_stack, save_course_to_file, validate_course_structure

# GitHub MCP Tools Configuration
def setup_github_mcp_tools():
    github_mcp_tools = MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://api.githubcopilot.com/mcp/",
            headers={
                "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
            },
        ),
        tool_filter=[
            "search_repositories",
            "get_repository", 
            "get_file_contents",
            "search_code",
            "list_branches",
            "get_tree"
        ],
    )
    return github_mcp_tools

# Enhanced Tech Stack Analysis with Repository Context
def analyze_repository_context(repo_url: str, technologies: str = "") -> dict:
    """
    Analyzes repository structure and tech stack for course context.
    This will be called by the agent to understand the codebase before generating examples.
    """
    # Extract repo info from URL
    if "github.com/" in repo_url:
        parts = repo_url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
        else:
            return {"error": "Invalid GitHub repository URL format"}
    else:
        return {"error": "Only GitHub repositories are supported"}
    
    analysis = {
        "repository": {
            "owner": owner,
            "name": repo,
            "url": repo_url
        },
        "technologies": technologies.split(",") if technologies else [],
        "analysis_timestamp": datetime.now().isoformat(),
        "suggested_examples": []
    }
    
    return analysis

# Enhanced Course Writer with Repository Integration
enhanced_course_writer = Agent(
    model=config.critic_model,
    name="enhanced_course_writer",
    description="Writes detailed course content with real code examples from connected repositories.",
    instruction="""
    You are an expert technical instructor creating detailed course content with real-world code examples.
    
    Based on the course outline in `course_outline` state, write comprehensive content for each lesson.
    
    IMPORTANT: If repository context is available in `repo_context` state, use the GitHub MCP tools to:
    1. Explore the repository structure using `list_repository_contents`
    2. Find relevant code files using `search_code` or `get_file_contents`
    3. Extract meaningful code examples that match the lesson content
    4. Include actual code snippets from the repository in your lessons
    
    For each lesson, create:
    - Clear explanations with examples
    - REAL code samples from the connected repository (when available)
    - Practical exercises based on the repository structure
    - Key takeaways and summary
    - Prerequisites and next steps
    
    When using repository code:
    - Always provide context about where the code comes from
    - Explain how the code relates to the lesson objectives
    - Adapt code examples to match the lesson's difficulty level
    - Include file paths and brief descriptions
    
    Content should be:
    - Engaging and suitable for self-paced learning
    - Technical but accessible at the specified difficulty level
    - Include real-world examples from the connected repository
    - Structured with headings and sections
    
    Output as JSON with lesson content:
    {
        "course_id": "generated_course_id",
        "repository_info": {
            "connected_repo": "repo_url",
            "examples_included": true/false
        },
        "modules": [
            {
                "module_id": "module_1",
                "title": "Module Title",
                "lessons": [
                    {
                        "lesson_id": "lesson_1_1",
                        "title": "Lesson Title",
                        "content": "Detailed markdown content...",
                        "code_examples": [
                            {
                                "source": "repository_file_path",
                                "code": "actual code snippet",
                                "explanation": "how this relates to the lesson"
                            }
                        ],
                        "exercises": ["exercise description"],
                        "resources": ["resource links"]
                    }
                ]
            }
        ]
    }
    """,
    tools=[],  # Will be added dynamically
    output_key="course_content",
)

# Main Interactive Course Agent with GitHub Integration
interactive_course_agent = Agent(
    name="interactive_course_agent",
    model=config.worker_model,
    description="Technical course creation assistant with GitHub repository integration for real code examples.",
    instruction=f"""
    You are a technical course creation assistant that can create comprehensive courses with real code examples from connected GitHub repositories.

    Your enhanced workflow is:
    1. **Repository Connection (Optional):** If the user provides a GitHub repository URL, use `analyze_repository_context` to understand the codebase structure.
    2. **Tech Stack Analysis:** Analyze provided technologies and repository context using `analyze_tech_stack`.
    3. **Plan:** Generate a course outline using `robust_course_planner`.
    4. **Refine:** Work with user to refine the outline.
    5. **Assessment Choice:** Ask user about including quizzes.
    6. **Write with Repository Integration:** Use `enhanced_course_writer` with GitHub MCP tools to create content with real code examples from the connected repository.
    7. **Edit:** Iterate on content based on feedback using `course_editor`.
    8. **Quizzes:** Generate assessments if requested using `robust_quiz_generator`.
    9. **Validate:** Validate course structure using `validate_course_structure`.
    10. **Export:** Save final course using `save_course_to_file`.

    **GitHub Repository Integration:**
    When a repository is connected, you can:
    - Browse repository structure and files
    - Search for specific code patterns
    - Extract relevant code examples for lessons
    - Provide context about real-world implementations
    - Create exercises based on actual codebase

    **Available GitHub MCP Tools:**
    - `search_repositories`: Find repositories
    - `get_repository`: Get repository details
    - `list_repository_contents`: Browse files and folders
    - `get_file_contents`: Read specific files
    - `search_code`: Search for code patterns
    - `list_branches`: See available branches

    Always explain to users how repository integration enhances the course with real examples.
    """,
    sub_agents=[
        robust_course_planner,
        enhanced_course_writer,
        course_editor,
        robust_quiz_generator,
    ],
    tools=[
        FunctionTool(save_course_to_file),
        FunctionTool(analyze_tech_stack),
        FunctionTool(analyze_repository_context),
        FunctionTool(validate_course_structure),
        setup_github_mcp_tools(),  # Add GitHub MCP tools
    ],
    output_key="course_outline",
)

root_agent = interactive_course_agent