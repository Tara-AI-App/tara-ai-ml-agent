from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import subprocess
import asyncio
import os

app = FastAPI(title="Course Generator API", version="1.0.0")

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

@app.post("/course/generate", response_model=CourseResponse)
async def generate_course(request: CourseRequest):
    """
    Generate a course with hardcoded response data.
    """
    # Hardcoded response as specified
    return CourseResponse(
        learning_objectives=[
            "Understand the fundamentals of Google Cloud Vertex AI.",
            "Train an XGBoost model for a real-world problem.",
            "Deploy an XGBoost model to a Vertex AI endpoint for online predictions.",
            "Perform batch predictions using Vertex AI for offline use cases.",
            "Integrate XGBoost with a complete MLOps workflow on GCP."
        ],
        description="Learn how to deploy machine learning models using XGBoost on Google Cloud Vertex AI.",
        estimated_duration=10,
        modules=[
            Module(
                lessons=[
                    Lesson(
                        content="This lesson introduces Google Cloud Vertex AI, a unified platform for machine learning development. We will explore the key components of Vertex AI, including notebooks, training, and model deployment.",
                        title="Introduction to Vertex AI",
                        index=1
                    )
                ],
                title="Module 1: Introduction to Vertex AI",
                index=1
            )
        ],
        title="Machine Learning Deployment with XGBoost and Vertex AI",
        source_from=[
            "https://github.com",
            "https://google.drive.com"
        ],
        difficulty="Advance"
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
