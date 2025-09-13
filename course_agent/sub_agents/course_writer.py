from google.adk.agents import Agent, LoopAgent
from google.adk.tools import google_search

from ..config import config
from ..agent_utils import suppress_output_callback
from ..validation_checkers import CourseContentValidationChecker

course_writer = Agent(
    model=config.critic_model,
    name="course_writer",
    description="Writes detailed course content for each lesson.",
    instruction="""
    You are an expert technical instructor creating detailed course content.
    
    Based on the course outline in `course_outline` state, write comprehensive content for each lesson.
    
    For each lesson, create:
    - Clear explanations with examples
    - Code samples when relevant (with syntax highlighting)
    - Practical exercises and projects
    - Key takeaways and summary
    - Prerequisites and next steps
    
    Content should be:
    - Engaging and suitable for self-paced learning
    - Technical but accessible at the specified difficulty level
    - Include real-world examples and use cases
    - Structured with headings and sections
    
    Use Google Search to find:
    - Current best practices and standards
    - Real-world examples and case studies
    - Updated documentation and references
    
    Output as JSON with lesson content:
    {
        "course_id": "generated_course_id",
        "modules": [
            {
                "module_id": "module_1",
                "title": "Module Title",
                "lessons": [
                    {
                        "lesson_id": "lesson_1_1",
                        "title": "Lesson Title",
                        "content": "Detailed markdown content...",
                        "code_examples": ["code snippet 1", "code snippet 2"],
                        "exercises": ["exercise description"],
                        "resources": ["resource links"]
                    }
                ]
            }
        ]
    }
    """,
    tools=[google_search],
    output_key="course_content",
    after_agent_callback=suppress_output_callback,
)

robust_course_writer = LoopAgent(
    name="robust_course_writer",
    description="A robust course writer that retries if it fails.",
    sub_agents=[
        course_writer,
        CourseContentValidationChecker(name="course_content_validation_checker"),
    ],
    max_iterations=3,
)