from typing import List, Dict, Any
from .interfaces import ResearchAgentInterface
from .tools import OpenAlexACMTool


class ACMAgent(ResearchAgentInterface):
    """
    ACM Scholar Agent: Search and discover ACM papers via OpenAlex API.
    """
    def search_papers(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return OpenAlexACMTool.search(query, limit)
        
    def ingest_paper(self, paper_url: str) -> Dict[str, Any]:
        filename = paper_url.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename += ".pdf"
        return {"success": True, "message": f"Ready to download {filename}"}


def get_agent() -> ResearchAgentInterface:
    """
    Returns the ACM Agent instance.
    """
    return ACMAgent()
