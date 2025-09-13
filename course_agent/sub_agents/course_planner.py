from google.adk.agents import Agent, LoopAgent
from google.adk.tools import google_search

from ..config import config
from ..agent_utils import suppress_output_callback
from ..validation_checkers import CourseOutlineValidationChecker

course_planner = Agent(
    model=config.worker_model,
    name="course_planner",
    description="Generates a structured course outline.",
    instruction="""
    You are a technical curriculum designer. Your job is to create a comprehensive course outline.
    
    The outline should be well-structured following this format:
    - Course title and description
    - Difficulty level (beginner/intermediate/advanced)
    - 5-8 modules with logical progression
    - 3-6 lessons per module
    - Learning objectives for each lesson
    - Estimated duration for each lesson (15-60 minutes)
    
    If technology stack information is provided in the `tech_analysis` state key, use it to:
    - Tailor the course content to specific technologies
    - Include relevant frameworks and tools
    - Suggest appropriate difficulty progression
    
    Use Google Search to find current best practices, tutorials, and industry standards.
    
    Output the course outline as a structured JSON with this format:
    {
        "title": "Course Title",
        "description": "Course description",
        "difficulty_level": "intermediate",
        "estimated_duration_hours": 20,
        "modules": [
            {
                "title": "Module Title",
                "description": "Module description",
                "order": 1,
                "lessons": [
                    {
                        "title": "Lesson Title",
                        "learning_objectives": ["objective1", "objective2"],
                        "duration_minutes": 30
                    }
                ]
            }
        ],
        "tags": ["tag1", "tag2"]
    }
    """,
    tools=[google_search],
    output_key="course_outline",
    after_agent_callback=suppress_output_callback,
)

robust_course_planner = LoopAgent(
    name="robust_course_planner",
    description="A robust course planner that retries if it fails.",
    sub_agents=[
        course_planner,
        CourseOutlineValidationChecker(name="course_outline_validation_checker"),
    ],
    max_iterations=3,
    after_agent_callback=suppress_output_callback,
)