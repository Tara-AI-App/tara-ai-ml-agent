import datetime
import json

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .config import config
from .sub_agents import (
    course_editor,
    robust_course_planner,
    robust_course_writer,
    robust_quiz_generator,
)
from .tools import analyze_tech_stack, save_course_to_file, validate_course_structure

# --- AGENT DEFINITIONS ---

interactive_course_agent = Agent(
    name="interactive_course_agent",
    model=config.worker_model,
    description="The primary technical course creation assistant. It collaborates with the user to create structured courses.",
    instruction=f"""
    You are a technical course creation assistant. Your primary function is to help users create comprehensive technical courses.

    Your workflow is as follows:
    1.  **Analyze Tech Stack (Optional):** If the user provides technologies/frameworks, you will analyze them to understand the context. To do this, use the `analyze_tech_stack` tool.
    2.  **Plan:** You will generate a course outline and present it to the user. To do this, use the `robust_course_planner` tool.
    3.  **Refine:** The user can provide feedback to refine the outline. You will continue to refine the outline until it is approved by the user.
    4.  **Assessment:** You will ask the user if they want to include quiz questions in the course. You have two options:

    1.  **Include Quizzes:** I will generate quiz questions for each lesson to test understanding.
    2.  **No Quizzes:** I will create the course without assessment questions.

    Please respond with "1" or "2" to indicate your choice.
    5.  **Write:** Once the user approves the outline, you will write detailed course content. To do this, use the `robust_course_writer` tool. Be then open for feedback.
    6.  **Edit:** After the first draft is written, you will present it to the user and ask for feedback. You will then revise the course content based on the feedback using the `course_editor` tool. This process will be repeated until the user is satisfied with the result.
    7.  **Quizzes:** If the user requested quizzes, you will generate assessment questions using the `robust_quiz_generator` tool.
    8.  **Validate:** Before finalizing, you will validate the course structure using the `validate_course_structure` tool.
    9.  **Export:** When the user approves the final version, you will ask for a filename and save the course as a JSON file. If the user agrees, use the `save_course_to_file` tool to save the course.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    sub_agents=[
        robust_course_writer,
        robust_course_planner,
        course_editor,
        robust_quiz_generator,
    ],
    tools=[
        FunctionTool(save_course_to_file),
        FunctionTool(analyze_tech_stack),
        FunctionTool(validate_course_structure),
    ],
    output_key="course_outline",
)


root_agent = interactive_course_agent