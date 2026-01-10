import requests
from typing import List, Dict, Any
from loguru import logger


class OpenAlexACMTool:
    """
    Tool for searching ACM papers via the OpenAlex API.
    """
    
    BASE_URL = "https://api.openalex.org/works"
    ACM_PUBLISHER_ID = "P4310319798"
    CS_CONCEPT_ID = "C41008148"
    
    @classmethod
    def search(cls, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for ACM Open Access papers.
        """
        filters = [
            f"primary_location.source.publisher_lineage:{cls.ACM_PUBLISHER_ID}",
            f"concepts.id:{cls.CS_CONCEPT_ID}",
            "is_oa:true",
            "type:article",
        ]
        
        params = {
            "search": query,
            "filter": ",".join(filters),
            "per_page": min(limit, 20),
            "sort": "cited_by_count:desc"
        }
        
        logger.info(f"[ACM-Agent] Searching: '{query}'")
        
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[ACM-Agent] Search failed: {e}")
            return []
        
        results = []
        for work in data.get('results', []):
            venue = work.get('primary_location', {}).get('source', {}).get('display_name', 'Unknown')
            pdf_url = cls._get_pdf_url(work)
            
            if not pdf_url:
                continue
                
            results.append({
                "title": work.get('title'),
                "year": work.get('publication_year'),
                "venue": venue,
                "citations": work.get('cited_by_count'),
                "pdf_url": pdf_url,
                "openalex_id": work.get('id'),
            })
        
        return results[:limit]

    @classmethod
    def _get_pdf_url(cls, work: Dict[str, Any]) -> str | None:
        """Get PDF URL from OpenAlex work data."""
        best_oa = work.get('best_oa_location', {})
        if best_oa and best_oa.get('pdf_url'):
            return best_oa.get('pdf_url')
        return None
