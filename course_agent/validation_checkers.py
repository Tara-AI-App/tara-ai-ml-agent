from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions


class CourseOutlineValidationChecker(BaseAgent):
    """Checks if the course outline is valid."""

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if context.session.state.get("course_outline"):
            yield Event(
                author=self.name,
                actions=EventActions(escalate=True),
            )
        else:
            yield Event(author=self.name)


class CourseContentValidationChecker(BaseAgent):
    """Checks if the course content is valid."""

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if context.session.state.get("course_content"):
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)


class CourseQuizValidationChecker(BaseAgent):
    """Checks if the course quizzes are valid."""

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if context.session.state.get("course_quizzes"):
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)