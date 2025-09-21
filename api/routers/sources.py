from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.models import (
    AssetModel,
    CreateSourceInsightRequest,
    SourceCreate,
    SourceInsightResponse,
    SourceListResponse,
    SourceResponse,
    SourceUpdate,
)
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import InvalidInputError
from open_notebook.graphs.source import source_graph

router = APIRouter()


@router.get("/sources", response_model=List[SourceListResponse])
async def get_sources(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
):
    """Get all sources with optional notebook filtering."""
    try:
        if notebook_id:
            # Get sources for a specific notebook
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")
            sources = await notebook.get_sources()
        else:
            # Get all sources
            sources = await Source.get_all(order_by="updated desc")

        # Create response list with async insights count
        response_list: List[SourceListResponse] = []
        for source in sources:
            insights = await source.get_insights()
            if source.id is None:
                logger.warning("Skipping source without id")
                continue
            response_list.append(
                SourceListResponse(
                    id=source.id,
                    title=source.title,
                    topics=source.topics or [],
                    asset=AssetModel(
                        file_path=source.asset.file_path if source.asset else None,
                        url=source.asset.url if source.asset else None,
                    )
                    if source.asset
                    else None,
                    embedded_chunks=await source.get_embedded_chunks(),
                    insights_count=len(insights),
                    created=str(source.created),
                    updated=str(source.updated),
                )
            )

        return response_list
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching sources: {str(e)}")


@router.post("/sources", response_model=SourceResponse)
async def create_source(source_data: SourceCreate):
    """Create a new source."""
    try:
        # Verify notebook exists
        notebook = await Notebook.get(source_data.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Prepare content_state for source_graph
        content_state: Dict[str, Any] = {}

        if source_data.type == "link":
            if not source_data.url:
                raise HTTPException(
                    status_code=400, detail="URL is required for link type"
                )
            content_state["url"] = source_data.url
        elif source_data.type == "upload":
            if not source_data.file_path:
                raise HTTPException(
                    status_code=400, detail="File path is required for upload type"
                )
            content_state["file_path"] = source_data.file_path
            content_state["delete_source"] = source_data.delete_source
        elif source_data.type == "text":
            if not source_data.content:
                raise HTTPException(
                    status_code=400, detail="Content is required for text type"
                )
            content_state["content"] = source_data.content
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source type. Must be link, upload, or text",
            )

        # Get transformations to apply
        transformations: List[Transformation] = []
        if source_data.transformations:
            for trans_id in source_data.transformations:
                transformation = await Transformation.get(trans_id)
                if not transformation:
                    raise HTTPException(
                        status_code=404, detail=f"Transformation {trans_id} not found"
                    )
                transformations.append(transformation)

        # Process source using the source_graph
        result = await source_graph.ainvoke(
            cast(
                Any,
                {
                    "content_state": content_state,
                    "notebook_id": source_data.notebook_id,
                    "apply_transformations": transformations,
                    "embed": source_data.embed,
                },
            )
        )

        source_obj = result.get("source")
        if not isinstance(source_obj, Source):
            raise HTTPException(
                status_code=500, detail="Source graph did not return a Source instance"
            )
        if source_obj.id is None:
            raise HTTPException(
                status_code=500,
                detail="Created source is missing an identifier",
            )

        return SourceResponse(
            id=source_obj.id,
            title=source_obj.title,
            topics=source_obj.topics or [],
            asset=AssetModel(
                file_path=source_obj.asset.file_path if source_obj.asset else None,
                url=source_obj.asset.url if source_obj.asset else None,
            )
            if source_obj.asset
            else None,
            full_text=source_obj.full_text,
            embedded_chunks=await source_obj.get_embedded_chunks(),
            created=str(source_obj.created),
            updated=str(source_obj.updated),
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating source: {str(e)}")


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str):
    """Get a specific source by ID."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        if source.id is None:
            raise HTTPException(
                status_code=500, detail="Source record is missing an identifier"
            )

        return SourceResponse(
            id=source.id,
            title=source.title,
            topics=source.topics or [],
            asset=AssetModel(
                file_path=source.asset.file_path if source.asset else None,
                url=source.asset.url if source.asset else None,
            )
            if source.asset
            else None,
            full_text=source.full_text,
            embedded_chunks=await source.get_embedded_chunks(),
            created=str(source.created),
            updated=str(source.updated),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching source: {str(e)}")


@router.put("/sources/{source_id}", response_model=SourceResponse)
async def update_source(source_id: str, source_update: SourceUpdate):
    """Update a source."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Update only provided fields
        if source_update.title is not None:
            source.title = source_update.title
        if source_update.topics is not None:
            source.topics = source_update.topics

        await source.save()

        if source.id is None:
            raise HTTPException(
                status_code=500, detail="Source record is missing an identifier"
            )

        return SourceResponse(
            id=source.id,
            title=source.title,
            topics=source.topics or [],
            asset=AssetModel(
                file_path=source.asset.file_path if source.asset else None,
                url=source.asset.url if source.asset else None,
            )
            if source.asset
            else None,
            full_text=source.full_text,
            embedded_chunks=await source.get_embedded_chunks(),
            created=str(source.created),
            updated=str(source.updated),
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating source: {str(e)}")


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    """Delete a source."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        await source.delete()

        return {"message": "Source deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting source: {str(e)}")


@router.get("/sources/{source_id}/insights", response_model=List[SourceInsightResponse])
async def get_source_insights(source_id: str):
    """Get all insights for a specific source."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        insights = await source.get_insights()
        responses: List[SourceInsightResponse] = []
        for insight in insights:
            if insight.id is None:
                logger.warning("Skipping insight without id")
                continue
            responses.append(
                SourceInsightResponse(
                    id=insight.id,
                    source_id=source_id,
                    insight_type=insight.insight_type,
                    content=insight.content,
                    created=str(insight.created),
                    updated=str(insight.updated),
                )
            )
        return responses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching insights for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching insights: {str(e)}")


@router.post("/sources/{source_id}/insights", response_model=SourceInsightResponse)
async def create_source_insight(
    source_id: str,
    request: CreateSourceInsightRequest
):
    """Create a new insight for a source by running a transformation."""
    try:
        # Get source
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Get transformation
        transformation = await Transformation.get(request.transformation_id)
        if not transformation:
            raise HTTPException(status_code=404, detail="Transformation not found")
        
        # Run transformation graph
        from open_notebook.graphs.transformation import graph as transform_graph
        await transform_graph.ainvoke(
            cast(Any, dict(source=source, transformation=transformation))
        )
        
        # Get the newly created insight (last one)
        insights = await source.get_insights()
        if insights:
            newest = insights[-1]
            if newest.id is None:
                raise HTTPException(
                    status_code=500,
                    detail="Created insight is missing an identifier",
                )
            return SourceInsightResponse(
                id=newest.id,
                source_id=source_id,
                insight_type=newest.insight_type,
                content=newest.content,
                created=str(newest.created),
                updated=str(newest.updated),
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create insight")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating insight for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating insight: {str(e)}")
