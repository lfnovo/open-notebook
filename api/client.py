"""
API client for Open Notebook API.
This module provides a client interface to interact with the Open Notebook API.
"""

import os
from typing import Dict, List, Optional

import httpx
from loguru import logger


class APIClient:
    """Client for Open Notebook API."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:5055")
        self.timeout = 30.0
        # Add authentication header if password is set
        self.headers = {}
        password = os.getenv("OPEN_NOTEBOOK_PASSWORD")
        if password:
            self.headers["Authorization"] = f"Bearer {password}"

    def _make_request(
        self, method: str, endpoint: str, timeout: Optional[float] = None, **kwargs
    ) -> Dict:
        """Make HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"
        request_timeout = timeout if timeout is not None else self.timeout
        
        # Merge headers
        headers = kwargs.get("headers", {})
        headers.update(self.headers)
        kwargs["headers"] = headers

        try:
            with httpx.Client(timeout=request_timeout) as client:
                response = client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Request error for {method} {url}: {str(e)}")
            raise ConnectionError(f"Failed to connect to API: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error {e.response.status_code} for {method} {url}: {e.response.text}"
            )
            raise RuntimeError(
                f"API request failed: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {str(e)}")
            raise

    # Notebooks API methods
    def get_notebooks(
        self, archived: Optional[bool] = None, order_by: str = "updated desc"
    ) -> List[Dict]:
        """Get all notebooks."""
        params = {"order_by": order_by}
        if archived is not None:
            params["archived"] = archived

        return self._make_request("GET", "/api/notebooks", params=params)

    def create_notebook(self, name: str, description: str = "") -> Dict:
        """Create a new notebook."""
        data = {"name": name, "description": description}
        return self._make_request("POST", "/api/notebooks", json=data)

    def get_notebook(self, notebook_id: str) -> Dict:
        """Get a specific notebook."""
        return self._make_request("GET", f"/api/notebooks/{notebook_id}")

    def update_notebook(self, notebook_id: str, **updates) -> Dict:
        """Update a notebook."""
        return self._make_request("PUT", f"/api/notebooks/{notebook_id}", json=updates)

    def delete_notebook(self, notebook_id: str) -> Dict:
        """Delete a notebook."""
        return self._make_request("DELETE", f"/api/notebooks/{notebook_id}")

    # Search API methods
    def search(
        self,
        query: str,
        search_type: str = "text",
        limit: int = 100,
        search_sources: bool = True,
        search_notes: bool = True,
        minimum_score: float = 0.2,
    ) -> Dict:
        """Search the knowledge base."""
        data = {
            "query": query,
            "type": search_type,
            "limit": limit,
            "search_sources": search_sources,
            "search_notes": search_notes,
            "minimum_score": minimum_score,
        }
        return self._make_request("POST", "/api/search", json=data)

    def ask_simple(
        self,
        question: str,
        strategy_model: str,
        answer_model: str,
        final_answer_model: str,
    ) -> Dict:
        """Ask the knowledge base a question (simple, non-streaming)."""
        data = {
            "question": question,
            "strategy_model": strategy_model,
            "answer_model": answer_model,
            "final_answer_model": final_answer_model,
        }
        # Use 5 minute timeout for long-running ask operations
        return self._make_request(
            "POST", "/api/search/ask/simple", json=data, timeout=300.0
        )

    # Models API methods
    def get_models(self, model_type: Optional[str] = None) -> List[Dict]:
        """Get all models with optional type filtering."""
        params = {}
        if model_type:
            params["type"] = model_type
        return self._make_request("GET", "/api/models", params=params)

    def create_model(self, name: str, provider: str, model_type: str) -> Dict:
        """Create a new model."""
        data = {
            "name": name,
            "provider": provider,
            "type": model_type,
        }
        return self._make_request("POST", "/api/models", json=data)

    def delete_model(self, model_id: str) -> Dict:
        """Delete a model."""
        return self._make_request("DELETE", f"/api/models/{model_id}")

    def get_default_models(self) -> Dict:
        """Get default model assignments."""
        return self._make_request("GET", "/api/models/defaults")

    def update_default_models(self, **defaults) -> Dict:
        """Update default model assignments."""
        return self._make_request("PUT", "/api/models/defaults", json=defaults)

    # Transformations API methods
    def get_transformations(self) -> List[Dict]:
        """Get all transformations."""
        return self._make_request("GET", "/api/transformations")

    def create_transformation(
        self,
        name: str,
        title: str,
        description: str,
        prompt: str,
        apply_default: bool = False,
    ) -> Dict:
        """Create a new transformation."""
        data = {
            "name": name,
            "title": title,
            "description": description,
            "prompt": prompt,
            "apply_default": apply_default,
        }
        return self._make_request("POST", "/api/transformations", json=data)

    def get_transformation(self, transformation_id: str) -> Dict:
        """Get a specific transformation."""
        return self._make_request("GET", f"/api/transformations/{transformation_id}")

    def update_transformation(self, transformation_id: str, **updates) -> Dict:
        """Update a transformation."""
        return self._make_request(
            "PUT", f"/api/transformations/{transformation_id}", json=updates
        )

    def delete_transformation(self, transformation_id: str) -> Dict:
        """Delete a transformation."""
        return self._make_request("DELETE", f"/api/transformations/{transformation_id}")

    def execute_transformation(
        self, transformation_id: str, input_text: str, model_id: str
    ) -> Dict:
        """Execute a transformation on input text."""
        data = {
            "transformation_id": transformation_id,
            "input_text": input_text,
            "model_id": model_id,
        }
        # Use extended timeout for transformation operations
        return self._make_request(
            "POST", "/api/transformations/execute", json=data, timeout=120.0
        )

    # Notes API methods
    def get_notes(self, notebook_id: Optional[str] = None) -> List[Dict]:
        """Get all notes with optional notebook filtering."""
        params = {}
        if notebook_id:
            params["notebook_id"] = notebook_id
        return self._make_request("GET", "/api/notes", params=params)

    def create_note(
        self,
        content: str,
        title: Optional[str] = None,
        note_type: str = "human",
        notebook_id: Optional[str] = None,
    ) -> Dict:
        """Create a new note."""
        data = {
            "content": content,
            "note_type": note_type,
        }
        if title:
            data["title"] = title
        if notebook_id:
            data["notebook_id"] = notebook_id
        return self._make_request("POST", "/api/notes", json=data)

    def get_note(self, note_id: str) -> Dict:
        """Get a specific note."""
        return self._make_request("GET", f"/api/notes/{note_id}")

    def update_note(self, note_id: str, **updates) -> Dict:
        """Update a note."""
        return self._make_request("PUT", f"/api/notes/{note_id}", json=updates)

    def delete_note(self, note_id: str) -> Dict:
        """Delete a note."""
        return self._make_request("DELETE", f"/api/notes/{note_id}")

    # Embedding API methods
    def embed_content(self, item_id: str, item_type: str) -> Dict:
        """Embed content for vector search."""
        data = {
            "item_id": item_id,
            "item_type": item_type,
        }
        # Use extended timeout for embedding operations
        return self._make_request("POST", "/api/embed", json=data, timeout=120.0)

    # Settings API methods
    def get_settings(self) -> Dict:
        """Get all application settings."""
        return self._make_request("GET", "/api/settings")

    def update_settings(self, **settings) -> Dict:
        """Update application settings."""
        return self._make_request("PUT", "/api/settings", json=settings)

    # Context API methods
    def get_notebook_context(
        self, notebook_id: str, context_config: Optional[Dict] = None
    ) -> Dict:
        """Get context for a notebook."""
        data = {"notebook_id": notebook_id}
        if context_config:
            data["context_config"] = context_config
        return self._make_request(
            "POST", f"/api/notebooks/{notebook_id}/context", json=data
        )

    # Sources API methods
    def get_sources(self, notebook_id: Optional[str] = None) -> List[Dict]:
        """Get all sources with optional notebook filtering."""
        params = {}
        if notebook_id:
            params["notebook_id"] = notebook_id
        return self._make_request("GET", "/api/sources", params=params)

    def create_source(
        self,
        notebook_id: str,
        source_type: str,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
        content: Optional[str] = None,
        title: Optional[str] = None,
        transformations: Optional[List[str]] = None,
        embed: bool = False,
        delete_source: bool = False,
    ) -> Dict:
        """Create a new source."""
        data = {
            "notebook_id": notebook_id,
            "type": source_type,
            "embed": embed,
            "delete_source": delete_source,
        }
        if url:
            data["url"] = url
        if file_path:
            data["file_path"] = file_path
        if content:
            data["content"] = content
        if title:
            data["title"] = title
        if transformations:
            data["transformations"] = transformations

        return self._make_request("POST", "/api/sources", json=data)

    def get_source(self, source_id: str) -> Dict:
        """Get a specific source."""
        return self._make_request("GET", f"/api/sources/{source_id}")

    def update_source(self, source_id: str, **updates) -> Dict:
        """Update a source."""
        return self._make_request("PUT", f"/api/sources/{source_id}", json=updates)

    def delete_source(self, source_id: str) -> Dict:
        """Delete a source."""
        return self._make_request("DELETE", f"/api/sources/{source_id}")

    # Insights API methods
    def get_source_insights(self, source_id: str) -> List[Dict]:
        """Get all insights for a specific source."""
        return self._make_request("GET", f"/api/sources/{source_id}/insights")

    def get_insight(self, insight_id: str) -> Dict:
        """Get a specific insight."""
        return self._make_request("GET", f"/api/insights/{insight_id}")

    def delete_insight(self, insight_id: str) -> Dict:
        """Delete a specific insight."""
        return self._make_request("DELETE", f"/api/insights/{insight_id}")

    def save_insight_as_note(
        self, insight_id: str, notebook_id: Optional[str] = None
    ) -> Dict:
        """Convert an insight to a note."""
        data = {}
        if notebook_id:
            data["notebook_id"] = notebook_id
        return self._make_request(
            "POST", f"/api/insights/{insight_id}/save-as-note", json=data
        )

    def create_source_insight(
        self, source_id: str, transformation_id: str, model_id: Optional[str] = None
    ) -> Dict:
        """Create a new insight for a source by running a transformation."""
        data = {"transformation_id": transformation_id}
        if model_id:
            data["model_id"] = model_id
        return self._make_request(
            "POST", f"/api/sources/{source_id}/insights", json=data
        )

    # Episode Profiles API methods
    def get_episode_profiles(self) -> List[Dict]:
        """Get all episode profiles."""
        return self._make_request("GET", "/api/episode-profiles")

    def get_episode_profile(self, profile_name: str) -> Dict:
        """Get a specific episode profile by name."""
        return self._make_request("GET", f"/api/episode-profiles/{profile_name}")

    def create_episode_profile(
        self,
        name: str,
        description: str = "",
        speaker_config: str = "",
        outline_provider: str = "",
        outline_model: str = "",
        transcript_provider: str = "",
        transcript_model: str = "",
        default_briefing: str = "",
        num_segments: int = 5,
    ) -> Dict:
        """Create a new episode profile."""
        data = {
            "name": name,
            "description": description,
            "speaker_config": speaker_config,
            "outline_provider": outline_provider,
            "outline_model": outline_model,
            "transcript_provider": transcript_provider,
            "transcript_model": transcript_model,
            "default_briefing": default_briefing,
            "num_segments": num_segments,
        }
        return self._make_request("POST", "/api/episode-profiles", json=data)

    def update_episode_profile(self, profile_id: str, **updates) -> Dict:
        """Update an episode profile."""
        return self._make_request("PUT", f"/api/episode-profiles/{profile_id}", json=updates)

    def delete_episode_profile(self, profile_id: str) -> Dict:
        """Delete an episode profile."""
        return self._make_request("DELETE", f"/api/episode-profiles/{profile_id}")


# Global client instance
api_client = APIClient()
