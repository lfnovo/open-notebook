from typing import List, Dict, Protocol, Any


class ResearchAgentInterface(Protocol):
    """
    Standard interface for the Research Agent.
    """
    
    def search_papers(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for papers in the target knowledge base (e.g., ACM).
        
        Args:
            query: The search string.
            limit: Max number of results.
            
        Returns:
            List of paper objects (title, url, year, etc.)
        """
        ...
        
    def ingest_paper(self, paper_url: str) -> Dict[str, Any]:
        """
        Download and ingest a paper into the system.
        
        Args:
            paper_url: The direct URL to the PDF.
            
        Returns:
            Status dictionary (e.g., {"success": True, "document_id": "..."})
        """
        ...
