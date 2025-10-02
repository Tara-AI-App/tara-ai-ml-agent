from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import subprocess
import os
import json
import re

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("WARNING: python-dotenv not installed. Install with: pip install python-dotenv")

# Import ADK course agent
from course_agent.agents.course_agent import create_course_agent

app = FastAPI(title="Course Generator API", version="1.0.0")

# Ensure required environment variables are set
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    print("WARNING: GOOGLE_CLOUD_PROJECT environment variable not set. Add it to your .env file.")

class CourseRequest(BaseModel):
    token_github: str
    token_drive: str
    prompt: str
    files_url: str

class GitHubMCPRequest(BaseModel):
    token_github: str

class GitHubMCPResponse(BaseModel):
    status: str
    message: str
    container_id: str = None

class Lesson(BaseModel):
    content: str
    title: str
    index: int

class Module(BaseModel):
    lessons: List[Lesson]
    title: str
    index: int

class CourseResponse(BaseModel):
    learning_objectives: List[str]
    description: str
    estimated_duration: int
    modules: List[Module]
    title: str
    source_from: List[str]
    difficulty: str

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract JSON from agent response text.

    The agent may return JSON wrapped in markdown code blocks or mixed with other text.
    This function attempts to extract and parse the JSON.
    """
    # Try to find JSON in markdown code blocks first
    json_block_pattern = r'```json\s*(\{.*?\})\s*```'
    match = re.search(json_block_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON in code block failed to parse: {e}")

    # Try to find raw JSON object (greedy, may be incomplete)
    # Find the first { and try to find matching }
    start_idx = text.find('{')
    if start_idx != -1:
        # Try to find the matching closing brace
        brace_count = 0
        in_string = False
        escape_next = False

        for i in range(start_idx, len(text)):
            char = text[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found matching closing brace
                        json_str = text[start_idx:i+1]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Extracted JSON failed to parse: {e}")
                            # Try without trailing characters
                            break

    # Try parsing the entire text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠️  Full text JSON parse failed: {e}")
        raise ValueError("Could not extract valid JSON from agent response")


async def _run_agent_with_tools_async(agent, prompt: str) -> str:
    """
    Run the agent with full tool support using InMemoryRunner properly.

    Based on ADK api_server pattern:
    1. Create session
    2. Send message via run_async
    3. Collect all event content
    """
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    import uuid

    # Create runner (it manages its own services internally)
    runner = InMemoryRunner(agent=agent)

    # Generate IDs
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())


    # Step 1: Create session
    await runner.session_service.create_session(
        user_id=user_id,
        session_id=session_id,
        app_name=runner.app_name
    )

    # Step 2: Create user message
    new_message = types.Content(
        role="user",
        parts=[types.Part(text=prompt)]
    )

    # Step 3: Run and collect all events
    response_text = ""

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            # Extract text from event content
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text

    except Exception as e:
        raise RuntimeError(f"Agent execution failed: {e}")

    return response_text


@app.post("/course/generate", response_model=CourseResponse)
async def generate_course(request: CourseRequest):
    """
    Generate a course using the ADK course agent.

    This endpoint:
    1. Creates a course agent with the provided GitHub token
    2. Sends the user's prompt to the agent using InMemoryRunner
    3. Extracts and returns the generated course JSON
    """
    try:
        # Create course agent with provided tokens
        course_agent_instance = create_course_agent(
            github_token=request.token_github if request.token_github else None,
            drive_token=request.token_drive if request.token_drive else None
        )

        # Get the ADK agent
        agent = course_agent_instance.get_agent()

        # Run agent with full tool support (RAG, GitHub MCP, Search)
        response_text = await _run_agent_with_tools_async(agent, request.prompt)

        # If response is empty, provide helpful error
        if not response_text or response_text.strip() == "":
            raise ValueError("Agent returned empty response. Check that GOOGLE_CLOUD_PROJECT is set correctly.")

        # Try to extract JSON from the response
        course_json = extract_json_from_text(response_text)

        # Fix schema issues
        # 1. Fix estimated_duration if it's a string
        if isinstance(course_json.get('estimated_duration'), str):
            duration_str = course_json['estimated_duration']
            # Extract number from string like "10 hours" or "8-12 hours"
            import re
            match = re.search(r'(\d+)', duration_str)
            if match:
                course_json['estimated_duration'] = int(match.group(1))
            else:
                course_json['estimated_duration'] = 8  # Default

        # 2. Add missing index fields to modules and lessons
        if 'modules' in course_json:
            for mod_idx, module in enumerate(course_json['modules'], 1):
                if 'index' not in module:
                    module['index'] = mod_idx
                if 'lessons' in module:
                    for lesson_idx, lesson in enumerate(module['lessons'], 1):
                        if 'index' not in lesson:
                            lesson['index'] = lesson_idx

        # Validate and return the course
        return CourseResponse(**course_json)

    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse course from agent response: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Course generation failed: {str(e)}"
        )

@app.post("/mcp/github", response_model=GitHubMCPResponse)
async def provision_github_mcp(request: GitHubMCPRequest):
    """
    Provision a GitHub MCP server Docker container.
    """
    try:
        # Build the docker command - use 'docker' since it's in PATH inside container
        # Connect to the same network as this container for communication
        docker_cmd = [
            "docker", "run", "-i", "--rm", "-d",
            "--network", "tara-ai-ml-agent_course-agent-network",
            "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={request.token_github}",
            "-e", "GITHUB_READ_ONLY=1",
            "ghcr.io/github/github-mcp-server"
        ]
        
        # Get current environment
        env = os.environ.copy()
        
        # Execute the docker command
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        if result.returncode == 0:
            container_id = result.stdout.strip()
            return GitHubMCPResponse(
                status="success",
                message="GitHub MCP server container provisioned successfully",
                container_id=container_id
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to provision container: {result.stderr}"
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Docker command timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error provisioning container: {str(e)}"
        )

@app.get("/")
async def root():
    """
    Root endpoint for health check.
    """
    return {"message": "Course Generator API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
