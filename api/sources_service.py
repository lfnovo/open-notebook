"""
Sources service layer using API.
"""

from typing import Dict, List, Optional

from loguru import logger

from api.client import api_client
from open_notebook.domain.notebook import Asset, Source


class SourcesService:
    """Service layer for sources operations using API."""

    def __init__(self):
        logger.info("Using API for sources operations")

    def get_all_sources(self, notebook_id: Optional[str] = None) -> List[Source]:
        """Get all sources with optional notebook filtering."""
        sources_data = api_client.get_sources(notebook_id=notebook_id)
        # Convert API response to Source objects
        sources = []
        for source_data in sources_data:
            source = Source(
                title=source_data["title"],
                topics=source_data["topics"],
                asset=Asset(
                    file_path=source_data["asset"]["file_path"]
                    if source_data["asset"]
                    else None,
                    url=source_data["asset"]["url"] if source_data["asset"] else None,
                )
                if source_data["asset"]
                else None,
            )
            source.id = source_data["id"]
            source.created = source_data["created"]
            source.updated = source_data["updated"]
            sources.append(source)
        return sources

    def get_source(self, source_id: str) -> Source:
        """Get a specific source."""
        source_data = api_client.get_source(source_id)
        source = Source(
            title=source_data["title"],
            topics=source_data["topics"],
            full_text=source_data["full_text"],
            asset=Asset(
                file_path=source_data["asset"]["file_path"]
                if source_data["asset"]
                else None,
                url=source_data["asset"]["url"] if source_data["asset"] else None,
            )
            if source_data["asset"]
            else None,
        )
        source.id = source_data["id"]
        source.created = source_data["created"]
        source.updated = source_data["updated"]
        return source

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
    ) -> Source:
        """Create a new source."""
        source_data = api_client.create_source(
            notebook_id=notebook_id,
            source_type=source_type,
            url=url,
            file_path=file_path,
            content=content,
            title=title,
            transformations=transformations,
            embed=embed,
            delete_source=delete_source,
        )

        source = Source(
            title=source_data["title"],
            topics=source_data["topics"],
            full_text=source_data["full_text"],
            asset=Asset(
                file_path=source_data["asset"]["file_path"]
                if source_data["asset"]
                else None,
                url=source_data["asset"]["url"] if source_data["asset"] else None,
            )
            if source_data["asset"]
            else None,
        )
        source.id = source_data["id"]
        source.created = source_data["created"]
        source.updated = source_data["updated"]
        return source

    def update_source(self, source: Source) -> Source:
        """Update a source."""
        updates = {
            "title": source.title,
            "topics": source.topics,
        }
        source_data = api_client.update_source(source.id, **updates)

        # Update the source object with the response
        source.title = source_data["title"]
        source.topics = source_data["topics"]
        source.updated = source_data["updated"]

        return source

    def delete_source(self, source_id: str) -> bool:
        """Delete a source."""
        api_client.delete_source(source_id)
        return True


# Global service instance
sources_service = SourcesService()
