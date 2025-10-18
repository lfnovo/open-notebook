"""
Notebook service layer using API.
"""

from typing import List, Optional

from loguru import logger

from api.client import api_client
from open_notebook.domain.notebook import Notebook


class NotebookService:
    """Service layer for notebook operations using API."""
    
    def __init__(self):
        logger.info("Using API for notebook operations")
    
    def get_all_notebooks(self, order_by: str = "updated desc") -> List[Notebook]:
        """Get all notebooks."""
        notebooks_data = api_client.get_notebooks(order_by=order_by)
        # Convert API response to Notebook objects
        notebooks = []
        for nb_data in notebooks_data:
            nb = Notebook(
                name=nb_data["name"],
                description=nb_data["description"],
                archived=nb_data["archived"],
            )
            nb.id = nb_data["id"]
            nb.created = nb_data["created"]
            nb.updated = nb_data["updated"]
            notebooks.append(nb)
        return notebooks
    
    def get_notebook(self, notebook_id: str) -> Optional[Notebook]:
        """Get a specific notebook."""
        response = api_client.get_notebook(notebook_id)
        nb_data = response if isinstance(response, dict) else response[0]
        nb = Notebook(
            name=nb_data["name"],
            description=nb_data["description"],
            archived=nb_data["archived"],
        )
        nb.id = nb_data["id"]
        nb.created = nb_data["created"]
        nb.updated = nb_data["updated"]
        return nb

    def create_notebook(self, name: str, description: str = "") -> Notebook:
        """Create a new notebook."""
        response = api_client.create_notebook(name, description)
        nb_data = response if isinstance(response, dict) else response[0]
        nb = Notebook(
            name=nb_data["name"],
            description=nb_data["description"],
            archived=nb_data["archived"],
        )
        nb.id = nb_data["id"]
        nb.created = nb_data["created"]
        nb.updated = nb_data["updated"]
        return nb
    
    def update_notebook(self, notebook: Notebook) -> Notebook:
        """Update a notebook."""
        updates = {
            "name": notebook.name,
            "description": notebook.description,
            "archived": notebook.archived,
        }
        response = api_client.update_notebook(notebook.id or "", **updates)
        nb_data = response if isinstance(response, dict) else response[0]
        # Update the notebook object with the response
        notebook.name = nb_data["name"]
        notebook.description = nb_data["description"]
        notebook.archived = nb_data["archived"]
        notebook.updated = nb_data["updated"]
        return notebook
    
    def delete_notebook(self, notebook: Notebook) -> bool:
        """Delete a notebook."""
        api_client.delete_notebook(notebook.id or "")
        return True


# Global service instance
notebook_service = NotebookService()