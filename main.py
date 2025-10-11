from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import subprocess
import os
import json
import re
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("WARNING: python-dotenv not installed. Install with: pip install python-dotenv")

# Import ADK course agent
from course_agent.agents.course_agent import create_course_agent
from course_agent.tools.drive_tool import CredentialsManager

app = FastAPI(title="Course Generator API", version="1.0.0")

# Initialize credentials manager
CREDENTIALS_BASE_PATH = os.getenv("CREDENTIALS_BASE_PATH", "/credentials")
credentials_manager = CredentialsManager(base_path=CREDENTIALS_BASE_PATH)

# Ensure required environment variables are set
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    print("WARNING: GOOGLE_CLOUD_PROJECT environment variable not set. Add it to your .env file.")

class CourseRequest(BaseModel):
    user_id: str
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

class QuizChoice(BaseModel):
    A: str
    B: str
    C: str
    D: str = None  # Optional fourth choice

class Quiz(BaseModel):
    question: str
    choices: QuizChoice
    answer: str  # Should be "A", "B", "C", or "D"

class Module(BaseModel):
    lessons: List[Lesson]
    title: str
    index: int
    quiz: List[Quiz]

class CourseResponse(BaseModel):
    learning_objectives: List[str]
    description: str
    estimated_duration: int
    modules: List[Module]
    title: str
    source_from: List[str]
    difficulty: str
    skills: List[str]

def repair_json_string(json_str: str) -> str:
    """
    Attempt to repair common JSON issues, including incomplete JSON.
    """
    # Remove trailing commas before } or ]
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

    # Remove any text before first { and after last }
    start = json_str.find('{')
    end = json_str.rfind('}')
    if start != -1 and end != -1:
        json_str = json_str[start:end+1]

    # Try to complete incomplete JSON by counting braces
    if start != -1:
        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False

        for i in range(len(json_str)):
            char = json_str[i]

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
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1

        # If JSON is incomplete, try to close it
        if brace_count > 0 or bracket_count > 0:
            # Truncate to last complete element to avoid mid-string corruption
            # Find last complete comma or closing brace/bracket
            last_safe_pos = len(json_str)
            for i in range(len(json_str) - 1, -1, -1):
                if json_str[i] in [',', '}', ']'] and not in_string:
                    last_safe_pos = i + 1
                    break

            json_str = json_str[:last_safe_pos]

            # Recalculate counts after truncation
            brace_count = bracket_count = 0
            in_string = escape_next = False
            for char in json_str:
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
                    elif char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1

            # Close open brackets and braces
            json_str += ']' * bracket_count
            json_str += '}' * brace_count

    return json_str

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract JSON from agent response text with multiple fallback strategies.
    """
    if not text or text.strip() == "":
        raise ValueError("Empty response from agent")

    def try_parse_json(json_str: str) -> Dict[str, Any]:
        """Try to parse JSON with repair attempts."""
        # First try direct parse
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try with repairs
            try:
                repaired = repair_json_string(json_str)
                return json.loads(repaired)
            except json.JSONDecodeError as e:
                raise e

    # Strategy 1: Try to find JSON in markdown code blocks with ```json
    json_block_pattern = r'```json\s*(\{.*\})\s*```'
    match = re.search(json_block_pattern, text, re.DOTALL)
    if match:
        try:
            return try_parse_json(match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 2: Try to find JSON in code blocks with ```
    code_block_pattern = r'```\s*(\{.*\})\s*```'
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        try:
            return try_parse_json(match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Try to find raw JSON object with brace matching
    start_idx = text.find('{')
    if start_idx != -1:
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
                            return try_parse_json(json_str)
                        except json.JSONDecodeError:
                            # Continue to try other strategies
                            break

    # Strategy 4: Try parsing the entire text as JSON
    try:
        return try_parse_json(text)
    except json.JSONDecodeError:
        # Strategy 5: Strip whitespace and try again
        try:
            return try_parse_json(text.strip())
        except json.JSONDecodeError:
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
    1. Creates a course agent with the provided GitHub and Drive tokens
    2. Saves Drive credentials to shared volume for user
    3. Provisions Drive MCP Docker container (for testing)
    4. Sends the user's prompt to the agent using InMemoryRunner
    5. Extracts and returns the generated course JSON
    """
    drive_credentials_path = None
    
    try:
        # Save user's Drive credentials to shared volume if provided
        if request.token_drive:
            drive_credentials_path = credentials_manager.save_drive_credentials(
                user_id=request.user_id,
                drive_token=request.token_drive
            )
            print(f"📁 Drive credentials saved for user {request.user_id} at: {drive_credentials_path}")
        
        # Create course agent with provided tokens
        course_agent_instance = create_course_agent(
            github_token=request.token_github if request.token_github else None,
            drive_token=request.token_drive if request.token_drive else None
        )

        # Get the ADK agent
        agent = course_agent_instance.get_agent()

        # Run agent with full tool support (RAG, GitHub MCP, Drive MCP, Search)
        response_text = await _run_agent_with_tools_async(agent, request.prompt)

        # If response is empty, provide helpful error
        if not response_text or response_text.strip() == "":
            raise ValueError("Agent returned empty response. Check that GOOGLE_CLOUD_PROJECT is set correctly.")

        # Try to extract JSON from the response
        try:
            course_json = extract_json_from_text(response_text)
        except ValueError as e:
            # Log the actual response for debugging
            print(f"❌ Failed to extract JSON. Response length: {len(response_text)} chars")
            print(f"📄 First 1000 chars:\n{response_text[:1000]}\n")
            print(f"📄 Last 500 chars:\n{response_text[-500:]}\n")
            raise e

        # Validate required top-level fields
        required_fields = ['title', 'description', 'difficulty', 'learning_objectives', 'modules', 'source_from']
        missing_fields = [f for f in required_fields if f not in course_json]
        if missing_fields:
            raise ValueError(f"Agent response missing required fields: {missing_fields}")

        # Ensure modules is a list
        if not isinstance(course_json.get('modules'), list):
            raise ValueError("'modules' must be a list")

        # Fix schema issues
        # 1. Fix estimated_duration if it's a string or missing
        if 'estimated_duration' not in course_json:
            course_json['estimated_duration'] = 10
        elif isinstance(course_json.get('estimated_duration'), str):
            duration_str = course_json['estimated_duration']
            # Extract number from string like "10 hours" or "8-12 hours"
            match = re.search(r'(\d+)', duration_str)
            if match:
                course_json['estimated_duration'] = int(match.group(1))
            else:
                course_json['estimated_duration'] = 10  # Default

        # 2. Add missing index fields to modules and lessons
        if 'modules' in course_json:
            for mod_idx, module in enumerate(course_json['modules'], 1):
                if 'index' not in module:
                    module['index'] = mod_idx

                # Ensure lessons exists
                if 'lessons' not in module:
                    module['lessons'] = []

                if 'lessons' in module and isinstance(module['lessons'], list):
                    for lesson_idx, lesson in enumerate(module['lessons'], 1):
                        if 'index' not in lesson:
                            lesson['index'] = lesson_idx

                # Ensure quiz field exists (default to empty list if not provided)
                if 'quiz' not in module:
                    module['quiz'] = []

        # 3. Ensure skills field exists (default to empty list if not provided)
        if 'skills' not in course_json:
            course_json['skills'] = []

        # 4. Ensure source_from is a list
        if not isinstance(course_json.get('source_from'), list):
            course_json['source_from'] = []

        # 5. Ensure learning_objectives is a list
        if not isinstance(course_json.get('learning_objectives'), list):
            course_json['learning_objectives'] = []

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

@app.get("/")
async def root():
    """
    Root endpoint for health check.
    """
    return {"message": "Course Generator API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
