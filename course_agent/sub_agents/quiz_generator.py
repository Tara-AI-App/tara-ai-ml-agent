from google.adk.agents import Agent, LoopAgent

from ..config import config
from ..agent_utils import suppress_output_callback
from ..validation_checkers import CourseQuizValidationChecker

quiz_generator = Agent(
    model=config.worker_model,
    name="quiz_generator",
    description="Generates quiz questions for course lessons.",
    instruction="""
    You are an assessment specialist creating quiz questions for technical courses.
    
    Based on the course content in `course_content` state, generate 3-5 quiz questions per lesson.
    
    Question types:
    - Multiple choice (4 options)
    - True/False
    - Code completion/debugging
    - Short answer (when appropriate)
    
    Each question should:
    - Test understanding of key concepts
    - Match the lesson's difficulty level
    - Include clear explanations for correct answers
    - Avoid trick questions or ambiguous wording
    
    Output as JSON:
    {
        "course_id": "course_id",
        "quizzes": [
            {
                "lesson_id": "lesson_1_1",
                "questions": [
                    {
                        "question": "Question text",
                        "type": "multiple_choice",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": 0,
                        "explanation": "Why this answer is correct"
                    }
                ]
            }
        ]
    }
    """,
    output_key="course_quizzes",
    after_agent_callback=suppress_output_callback,
)

robust_quiz_generator = LoopAgent(
    name="robust_quiz_generator",
    description="A robust quiz generator that retries if it fails.",
    sub_agents=[
        quiz_generator,
        CourseQuizValidationChecker(name="course_quiz_validation_checker"),
    ],
    max_iterations=3,
    after_agent_callback=suppress_output_callback,
)