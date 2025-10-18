"""
Sources service layer using API.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from loguru import logger

from api.client import api_client
from open_notebook.domain.notebook import Asset, Source


@dataclass
class SourceProcessingResult:
    """Result of source creation with optional async processing info."""
    source: Source
    is_async: bool = False
    command_id: Optional[str] = None
    status: Optional[str] = None
    processing_info: Optional[Dict] = None


@dataclass
class SourceWithMetadata:
    """Source object with additional metadata from API."""
    source: Source
    embedded_chunks: int
    
    # Expose common source properties for easy access
    @property
    def id(self):
        return self.source.id
    
    @property  
    def title(self):
        return self.source.title
        
    @title.setter
    def title(self, value):
        self.source.title = value
    
    @property
    def topics(self):
        return self.source.topics
    
    @property
    def asset(self):
        return self.source.asset
    
    @property
    def full_text(self):
        return self.source.full_text
    
    @property
    def created(self):
        return self.source.created
    
    @property
    def updated(self):
        return self.source.updated


class SourcesService:
    """Service layer for sources operations using API."""

    def __init__(self):
        logger.info("Using API for sources operations")

    def get_all_sources(self, notebook_id: Optional[str] = None) -> List[SourceWithMetadata]:
        """Get all sources with optional notebook filtering."""
        sources_data = api_client.get_sources(notebook_id=notebook_id)
        # Convert API response to SourceWithMetadata objects
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
            
            # Wrap in SourceWithMetadata
            source_with_metadata = SourceWithMetadata(
                source=source,
                embedded_chunks=source_data.get("embedded_chunks", 0)
            )
            sources.append(source_with_metadata)
        return sources

    def get_source(self, source_id: str) -> SourceWithMetadata:
        """Get a specific source."""
        response = api_client.get_source(source_id)
        source_data = response if isinstance(response, dict) else response[0]
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

        return SourceWithMetadata(
            source=source,
            embedded_chunks=source_data.get("embedded_chunks", 0)
        )

    def create_source(
        self,
        notebook_id: Optional[str] = None,
        source_type: str = "text",
        url: Optional[str] = None,
        file_path: Optional[str] = None,
        content: Optional[str] = None,
        title: Optional[str] = None,
        transformations: Optional[List[str]] = None,
        embed: bool = False,
        delete_source: bool = False,
        notebooks: Optional[List[str]] = None,
        async_processing: bool = False,
    ) -> Union[Source, SourceProcessingResult]:
        """
        Create a new source with support for async processing.
        
        Args:
            notebook_id: Single notebook ID (deprecated, use notebooks parameter)
            source_type: Type of source (link, upload, text)
            url: URL for link sources
            file_path: File path for upload sources
            content: Text content for text sources
            title: Optional source title
            transformations: List of transformation IDs to apply
            embed: Whether to embed content for vector search
            delete_source: Whether to delete uploaded file after processing
            notebooks: List of notebook IDs to add source to (preferred over notebook_id)
            async_processing: Whether to process source asynchronously
            
        Returns:
            Source object for sync processing (backward compatibility)
            SourceProcessingResult for async processing (contains additional metadata)
        """
        source_data = api_client.create_source(
            notebook_id=notebook_id,
            notebooks=notebooks,
            source_type=source_type,
            url=url,
            file_path=file_path,
            content=content,
            title=title,
            transformations=transformations,
            embed=embed,
            delete_source=delete_source,
            async_processing=async_processing,
        )

        # Create Source object from response
        response_data = source_data if isinstance(source_data, dict) else source_data[0]
        source = Source(
            title=response_data["title"],
            topics=response_data.get("topics") or [],
            full_text=response_data.get("full_text"),
            asset=Asset(
                file_path=response_data["asset"]["file_path"]
                if response_data.get("asset")
                else None,
                url=response_data["asset"]["url"]
                if response_data.get("asset")
                else None,
            )
            if response_data.get("asset")
            else None,
        )
        source.id = response_data["id"]
        source.created = response_data["created"]
        source.updated = response_data["updated"]

        # Check if this is an async processing response
        if response_data.get("command_id") or response_data.get("status") or response_data.get("processing_info"):
            # Ensure source_data is a dict for accessing attributes
            source_data_dict = source_data if isinstance(source_data, dict) else source_data[0]
            # Return enhanced result for async processing
            return SourceProcessingResult(
                source=source,
                is_async=True,
                command_id=source_data_dict.get("command_id"),
                status=source_data_dict.get("status"),
                processing_info=source_data_dict.get("processing_info"),
            )
        else:
            # Return simple Source for backward compatibility
            return source

    def get_source_status(self, source_id: str) -> Dict:
        """Get processing status for a source."""
        response = api_client.get_source_status(source_id)
        return response if isinstance(response, dict) else response[0]

    def create_source_async(
        self,
        notebook_id: Optional[str] = None,
        source_type: str = "text",
        url: Optional[str] = None,
        file_path: Optional[str] = None,
        content: Optional[str] = None,
        title: Optional[str] = None,
        transformations: Optional[List[str]] = None,
        embed: bool = False,
        delete_source: bool = False,
        notebooks: Optional[List[str]] = None,
    ) -> SourceProcessingResult:
        """
        Create a new source with async processing enabled.
        
        This is a convenience method that always uses async processing.
        Returns a SourceProcessingResult with processing status information.
        """
        result = self.create_source(
            notebook_id=notebook_id,
            notebooks=notebooks,
            source_type=source_type,
            url=url,
            file_path=file_path,
            content=content,
            title=title,
            transformations=transformations,
            embed=embed,
            delete_source=delete_source,
            async_processing=True,
        )
        
        # Since we forced async_processing=True, this should always be a SourceProcessingResult
        if isinstance(result, SourceProcessingResult):
            return result
        else:
            # Fallback: wrap Source in SourceProcessingResult
            return SourceProcessingResult(
                source=result,
                is_async=False,  # This shouldn't happen, but handle it gracefully
            )

    def is_source_processing_complete(self, source_id: str) -> bool:
        """
        Check if a source's async processing is complete.
        
        Returns True if processing is complete (success or failure),
        False if still processing or queued.
        """
        try:
            status_data = self.get_source_status(source_id)
            status = status_data.get("status")
            return status in ["completed", "failed", None]  # None indicates legacy/sync source
        except Exception as e:
            logger.error(f"Error checking source processing status: {e}")
            return True  # Assume complete on error

    def update_source(self, source: Source) -> Source:
        """Update a source."""
        if not source.id:
            raise ValueError("Source ID is required for update")
            
        updates = {
            "title": source.title,
            "topics": source.topics,
        }
        source_data = api_client.update_source(source.id, **updates)

        # Ensure source_data is a dict
        source_data_dict = source_data if isinstance(source_data, dict) else source_data[0]

        # Update the source object with the response
        source.title = source_data_dict["title"]
        source.topics = source_data_dict["topics"]
        source.updated = source_data_dict["updated"]

        return source

    def delete_source(self, source_id: str) -> bool:
        """Delete a source."""
        api_client.delete_source(source_id)
        return True


# Global service instance
sources_service = SourcesService()

# Export important classes for easy importing
__all__ = ["SourcesService", "SourceWithMetadata", "SourceProcessingResult", "sources_service"]
