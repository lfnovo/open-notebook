import os
from typing import List, Dict, Any
from .interfaces import ResearchAgentInterface
from .tools import OpenAlexACMTool

class LocalACMAgent(ResearchAgentInterface):
    """
    Open Source Implementation:
    Runs entirely on the user's machine. Uses the local OpenAlex tool directly.
    """
    def search_papers(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return OpenAlexACMTool.search(query, limit)
        
    def ingest_paper(self, paper_url: str) -> Dict[str, Any]:
        # In a real integration, this would call the Open Notebook File Service
        # For POC, we just simulate the download
        print(f"[LocalAgent] Simulating ingestion of {paper_url}")
        
        # Simulating a file path
        filename = paper_url.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename += ".pdf"
            
        # success = OpenAlexACMTool.download_pdf(paper_url, f"./data/sources/{filename}")
        success = True # Mock success
        
        if success:
            return {"success": True, "message": f"Downloaded {filename}", "status": "indexed"}
        return {"success": False, "message": "Download failed"}

    def health_check(self) -> bool:
        return True

class RemoteProAgent(ResearchAgentInterface):
    """
    Commercial/Enterprise Implementation:
    Stubs for future use. This would call a remote API service.
    """
    def __init__(self, api_key: str, endpoint: str = "https://api.acm-agent.com/v1"):
        self.api_key = api_key
        self.endpoint = endpoint
        
    def search_papers(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # This would be: requests.post(self.endpoint + "/search", ...)
        return [{"title": "Pro Feature Locked", "message": "Please upgrade to Pro"}]

    def ingest_paper(self, paper_url: str) -> Dict[str, Any]:
        return {"success": False, "message": "Pro Feature Locked"}

    def health_check(self) -> bool:
        # Check connection to remote server
        return False

class AgentFactory:
    """
    Factory to instantiate the correct agent based on configuration.
    This is the integration point for Open Notebook.
    """
    @staticmethod
    def get_agent() -> ResearchAgentInterface:
        """
        Determines which agent to load based on env vars.
        Defaults to Local (Open Source) mode.
        """
        mode = os.getenv("ACM_AGENT_MODE", "LOCAL").upper()
        
        if mode == "PRO":
            api_key = os.getenv("ACM_AGENT_API_KEY")
            if not api_key:
                print("⚠️  Warning: PRO mode requested but no API Key found. Falling back to LOCAL.")
                return LocalACMAgent()
            return RemoteProAgent(api_key=api_key)
            
        return LocalACMAgent()
