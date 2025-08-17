from typing import List, Optional

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
from open_notebook.database.repository import repo_query
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
        # Build the query
        if notebook_id:
            # Verify notebook exists first
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")

            # Query sources for specific notebook
            query = """
                SELECT id, asset, created, title, updated, topics,
                    (SELECT VALUE count() FROM source_insight WHERE source = $parent.id GROUP ALL)[0].count OR 0 AS insights_count,
                    ((SELECT VALUE count() FROM source_embedding WHERE source = $parent.id GROUP ALL)[0].count OR 0) > 0 AS embedded
                FROM source 
                WHERE id IN (SELECT source FROM reference WHERE notebook = $notebook_id)
                ORDER BY updated DESC
            """
            result = await repo_query(query, {"notebook_id": notebook_id})
        else:
            # Query all sources
            query = """
                SELECT id, asset, created, title, updated, topics,
                    (SELECT VALUE count() FROM source_insight WHERE source = $parent.id GROUP ALL)[0].count OR 0 AS insights_count,
                    ((SELECT VALUE count() FROM source_embedding WHERE source = $parent.id GROUP ALL)[0].count OR 0) > 0 AS embedded
                FROM source 
                ORDER BY updated DESC
            """
            result = await repo_query(query)

        # Convert result to response model
        response_list = []
        for row in result:
            response_list.append(
                SourceListResponse(
                    id=row["id"],
                    title=row.get("title"),
                    topics=row.get("topics") or [],
                    asset=AssetModel(
                        file_path=row["asset"].get("file_path")
                        if row.get("asset")
                        else None,
                        url=row["asset"].get("url") if row.get("asset") else None,
                    )
                    if row.get("asset")
                    else None,
                    embedded=row.get("embedded", False),
                    insights_count=row.get("insights_count", 0),
                    created=str(row["created"]),
                    updated=str(row["updated"]),
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
        content_state = {}

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
        transformations = []
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
            {
                "content_state": content_state,
                "notebook_id": source_data.notebook_id,
                "apply_transformations": transformations,
                "embed": source_data.embed,
            }
        )

        source = result["source"]

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
        logger.error(f"Error creating source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating source: {str(e)}")


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str):
    """Get a specific source by ID."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

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
        return [
            SourceInsightResponse(
                id=insight.id,
                source_id=source_id,
                insight_type=insight.insight_type,
                content=insight.content,
                created=str(insight.created),
                updated=str(insight.updated),
            )
            for insight in insights
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching insights for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching insights: {str(e)}"
        )


@router.post("/sources/{source_id}/insights", response_model=SourceInsightResponse)
async def create_source_insight(source_id: str, request: CreateSourceInsightRequest):
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
            input=dict(source=source, transformation=transformation)
        )

        # Get the newly created insight (last one)
        insights = await source.get_insights()
        if insights:
            newest = insights[-1]
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
