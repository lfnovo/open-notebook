import requests
from typing import List, Dict, Any
from loguru import logger

class OpenAlexACMTool:
    """
    Specialized tool for searching ACM (Association for Computing Machinery) 
    papers via the OpenAlex API.
    """
    
    BASE_URL = "https://api.openalex.org/works"
    
    # Verified IDs
    ACM_PUBLISHER_ID = "P4310319798"  # Association for Computing Machinery
    CS_CONCEPT_ID = "C41008148"       # Computer Science
    
    @classmethod
    def search(cls, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Executes the search with strict filters for ACM + Open Access.
        """
        # Strict Filters:
        # 1. Publisher = ACM
        # 2. Concept = Computer Science
        # 3. Open Access = True (Crucial for free access)
        # 4. Type = Article (Ignore datasets, etc.)
        filters = [
            f"primary_location.source.publisher_lineage:{cls.ACM_PUBLISHER_ID}",
            f"concepts.id:{cls.CS_CONCEPT_ID}",
            "is_oa:true",
            "type:article",
            "has_oa_accepted_or_published_version:true"  # Has OA version available
        ]
        
        params = {
            "search": query,
            "filter": ",".join(filters),
            "per_page": min(limit * 20, 100),  # Request many more to find papers with arXiv links
            "sort": "cited_by_count:desc"  # Prioritize impact over recency
        }
        
        logger.info(f"[ACM-Agent] Searching OpenAlex for: '{query}'...")
        
        import time
        for attempt in range(3):
            try:
                response = requests.get(cls.BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                break # Success
            except requests.exceptions.RequestException as e:
                logger.warning(f"[ACM-Agent] Attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return []
                time.sleep(1) # Wait before retry
        
        try:
            results = []
            for work in data.get('results', []):
                # Safe extraction of nested fields
                venue = work.get('primary_location', {}).get('source', {}).get('display_name', 'Unknown Venue')
                
                # Try to find a truly accessible PDF URL
                pdf_url = cls._get_accessible_pdf_url(work)
                
                # Only include results that actually have a working PDF link
                if not pdf_url:
                    continue
                    
                results.append({
                    "title": work.get('title'),
                    "year": work.get('publication_year'),
                    "venue": venue,
                    "citations": work.get('cited_by_count'),
                    "pdf_url": pdf_url,
                    "openalex_id": work.get('id'),
                    "abstract_index": bool(work.get('abstract_inverted_index')) # Flag if abstract exists
                })
            
            # Limit to requested number
            return results[:limit]

        except Exception as e:
            logger.error(f"[ACM-Agent] Error during search: {e}")
            return []

    # Trusted open access repositories that don't require authentication
    TRUSTED_OA_DOMAINS = [
        'arxiv.org',
        'ncbi.nlm.nih.gov',  # PubMed Central
        'europepmc.org',
        'biorxiv.org',
        'medrxiv.org',
        'zenodo.org',
        'figshare.com',
        'osf.io',
        'hal.science',
        'eprints.',
        'repository.',
        'dspace.',
    ]
    
    # Domains that often block direct downloads
    BLOCKED_DOMAINS = [
        'dl.acm.org',
        'ieeexplore.ieee.org',
        'sciencedirect.com',
        'springer.com',
        'wiley.com',
    ]
    
    @classmethod
    def _get_accessible_pdf_url(cls, work: Dict[str, Any]) -> str | None:
        """
        Find a truly accessible PDF URL from OpenAlex work data.
        Prioritizes trusted open repositories over publisher sites.
        """
        # Collect all available OA locations
        best_oa = work.get('best_oa_location', {})
        all_locations = work.get('locations', [])
        
        # Build list of candidate PDF URLs
        candidates = []
        
        # Add best_oa_location pdf_url
        if best_oa and best_oa.get('pdf_url'):
            candidates.append(best_oa.get('pdf_url'))
        
        # Add from all locations
        for loc in all_locations:
            if loc.get('pdf_url'):
                candidates.append(loc.get('pdf_url'))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for url in candidates:
            if url not in seen:
                seen.add(url)
                unique_candidates.append(url)
        candidates = unique_candidates
        
        # ONLY return trusted domains (arxiv, etc.) - ACM links return 403
        for url in candidates:
            if any(domain in url.lower() for domain in cls.TRUSTED_OA_DOMAINS):
                logger.debug(f"[ACM-Agent] Found trusted OA URL: {url}")
                return url
        
        # Skip papers without trusted OA links (ACM links don't work)
        logger.debug(f"[ACM-Agent] No trusted OA URL found, skipping paper")
        return None
    
    @staticmethod
    def download_pdf(url: str, save_path: str) -> bool:
        """
        Helper to download a PDF to a local path.
        """
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"[ACM-Agent] Download failed for {url}: {e}")
            return False
