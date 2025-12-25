from .core import AgentFactory
from .interfaces import ResearchAgentInterface

# Public API for the package
def get_research_agent() -> ResearchAgentInterface:
    """
    Main entry point. Returns the configured agent instance.
    """
    return AgentFactory.get_agent()
