from .core import get_agent, ACMAgent
from .interfaces import ResearchAgentInterface

# Public API for the package
def get_research_agent() -> ResearchAgentInterface:
    """
    Main entry point. Returns the ACM Agent instance.
    """
    return get_agent()
