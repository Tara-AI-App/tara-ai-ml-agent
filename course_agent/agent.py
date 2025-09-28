from .agents.course_agent import create_course_agent, CourseGenerationAgent
from .config.settings import settings
from .utils.logger import logger

# Create the main agent instance for backward compatibility
course_agent_instance = create_course_agent()

# Export the ADK agent for backward compatibility with existing code
root_agent = course_agent_instance.get_agent()

# Export main functions for direct use
analyze_tech_stack = course_agent_instance.analyze_tech_stack
discover_sources = course_agent_instance.discover_sources
extract_repository_content = course_agent_instance.extract_repository_content
get_tracked_sources = course_agent_instance.get_tracked_sources
determine_difficulty = course_agent_instance.determine_difficulty
save_course_to_file = course_agent_instance.save_course_to_file

# Export configuration and status functions
def get_agent_status():
    """Get comprehensive agent status and configuration."""
    return course_agent_instance.get_configuration_status()

def reload_configuration():
    """Reload configuration and recreate agent."""
    global course_agent_instance, root_agent
    course_agent_instance = create_course_agent()
    root_agent = course_agent_instance.get_agent()
    logger.info("Agent configuration reloaded")

# Log initialization
logger.info("Course Agent v2.0 initialized")
logger.info(f"Configuration status: {get_agent_status()}")

# Backward compatibility exports
__all__ = [
    'root_agent',
    'course_agent_instance',
    'analyze_tech_stack',
    'discover_sources',
    'extract_repository_content',
    'get_tracked_sources',
    'determine_difficulty',
    'save_course_to_file',
    'get_agent_status',
    'reload_configuration',
    'CourseGenerationAgent',
    'settings',
    'logger'
]