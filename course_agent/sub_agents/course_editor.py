from google.adk.agents import Agent

from ..config import config
from ..agent_utils import suppress_output_callback

course_editor = Agent(
    model=config.critic_model,
    name="course_editor",
    description="Edits course content based on user feedback.",
    instruction="""
    You are a professional curriculum editor. You will be given course content and user feedback.
    Your task is to revise the course content based on the provided feedback.
    
    Focus on:
    - Improving clarity and learning flow
    - Adjusting difficulty level if needed
    - Adding or removing content as requested
    - Fixing any technical inaccuracies
    - Enhancing practical examples and exercises
    
    Maintain the same JSON structure as the original course content.
    Ensure all revisions align with the course objectives and target audience.
    """,
    output_key="course_content",
    after_agent_callback=suppress_output_callback,
)