from typing import List, Optional

from ai_prompter import Prompter
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.models import GenerateOverviewRequest, ModuleCreate, ModuleResponse, ModuleUpdate
from backpack.ai.provision import provision_langchain_model
from backpack.database.repository import ensure_record_id, repo_query
from backpack.domain.module import Module, Source
from backpack.exceptions import InvalidInputError
from backpack.utils import clean_thinking_content

router = APIRouter()


@router.get("/modules", response_model=List[ModuleResponse])
async def get_modules(
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    order_by: str = Query("updated desc", description="Order by field and direction"),
):
    """Get all modules with optional filtering and ordering."""
    try:
        # Build the query with counts
        query = f"""
            SELECT *,
            count(<-reference.in) as source_count,
            count(<-artifact.in) as note_count
            FROM module
            ORDER BY {order_by}
        """

        result = await repo_query(query)

        # Filter by archived status if specified
        if archived is not None:
            result = [nb for nb in result if nb.get("archived") == archived]

        return [
            ModuleResponse(
                id=str(nb.get("id", "")),
                name=nb.get("name", ""),
                description=nb.get("description", ""),
                archived=nb.get("archived", False),
                overview=nb.get("overview"),
                created=str(nb.get("created", "")),
                updated=str(nb.get("updated", "")),
                source_count=nb.get("source_count", 0),
                note_count=nb.get("note_count", 0),
            )
            for nb in result
        ]
    except Exception as e:
        logger.error(f"Error fetching modules: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching modules: {str(e)}"
        )


@router.post("/modules", response_model=ModuleResponse)
async def create_module(module: ModuleCreate):
    """Create a new module."""
    try:
        new_module = Module(
            name=module.name,
            description=module.description,
        )
        await new_module.save()

        return ModuleResponse(
            id=new_module.id or "",
            name=new_module.name,
            description=new_module.description,
            archived=new_module.archived or False,
            overview=new_module.overview,
            created=str(new_module.created),
            updated=str(new_module.updated),
            source_count=0,  # New module has no sources
            note_count=0,  # New module has no notes
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating module: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating module: {str(e)}"
        )


@router.get("/modules/{module_id}", response_model=ModuleResponse)
async def get_module(module_id: str):
    """Get a specific module by ID."""
    try:
        # Query with counts for single module
        query = """
            SELECT *,
            count(<-reference.in) as source_count,
            count(<-artifact.in) as note_count
            FROM $module_id
        """
        result = await repo_query(query, {"module_id": ensure_record_id(module_id)})

        if not result:
            raise HTTPException(status_code=404, detail="Module not found")

        nb = result[0]
        return ModuleResponse(
            id=str(nb.get("id", "")),
            name=nb.get("name", ""),
            description=nb.get("description", ""),
            archived=nb.get("archived", False),
            overview=nb.get("overview"),
            created=str(nb.get("created", "")),
            updated=str(nb.get("updated", "")),
            source_count=nb.get("source_count", 0),
            note_count=nb.get("note_count", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching module {module_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching module: {str(e)}"
        )


@router.put("/modules/{module_id}", response_model=ModuleResponse)
async def update_module(module_id: str, module_update: ModuleUpdate):
    """Update a module."""
    try:
        module = await Module.get(module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        # Update only provided fields
        if module_update.name is not None:
            module.name = module_update.name
        if module_update.description is not None:
            module.description = module_update.description
        if module_update.archived is not None:
            module.archived = module_update.archived
        if module_update.overview is not None:
            module.overview = module_update.overview

        await module.save()

        # Query with counts after update
        query = """
            SELECT *,
            count(<-reference.in) as source_count,
            count(<-artifact.in) as note_count
            FROM $module_id
        """
        result = await repo_query(query, {"module_id": ensure_record_id(module_id)})

        if result:
            nb = result[0]
            return ModuleResponse(
                id=str(nb.get("id", "")),
                name=nb.get("name", ""),
                description=nb.get("description", ""),
                archived=nb.get("archived", False),
                overview=nb.get("overview"),
                created=str(nb.get("created", "")),
                updated=str(nb.get("updated", "")),
                source_count=nb.get("source_count", 0),
                note_count=nb.get("note_count", 0),
            )

        # Fallback if query fails
        return ModuleResponse(
            id=module.id or "",
            name=module.name,
            description=module.description,
            archived=module.archived or False,
            overview=module.overview,
            created=str(module.created),
            updated=str(module.updated),
            source_count=0,
            note_count=0,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating module {module_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating module: {str(e)}"
        )


@router.post("/modules/{module_id}/sources/{source_id}")
async def add_source_to_module(module_id: str, source_id: str):
    """Add an existing source to a module (create the reference)."""
    try:
        # Check if module exists
        module = await Module.get(module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        # Check if source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Check if reference already exists (idempotency)
        existing_ref = await repo_query(
            "SELECT * FROM reference WHERE out = $source_id AND in = $module_id",
            {
                "module_id": ensure_record_id(module_id),
                "source_id": ensure_record_id(source_id),
            },
        )

        # If reference doesn't exist, create it
        if not existing_ref:
            await repo_query(
                "RELATE $source_id->reference->$module_id",
                {
                    "module_id": ensure_record_id(module_id),
                    "source_id": ensure_record_id(source_id),
                },
            )

        return {"message": "Source linked to module successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error linking source {source_id} to module {module_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error linking source to module: {str(e)}"
        )


@router.delete("/modules/{module_id}/sources/{source_id}")
async def remove_source_from_module(module_id: str, source_id: str):
    """Remove a source from a module (delete the reference)."""
    try:
        # Check if module exists
        module = await Module.get(module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        # Delete the reference record linking source to module
        await repo_query(
            "DELETE FROM reference WHERE out = $module_id AND in = $source_id",
            {
                "module_id": ensure_record_id(module_id),
                "source_id": ensure_record_id(source_id),
            },
        )

        return {"message": "Source removed from module successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error removing source {source_id} from module {module_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error removing source from module: {str(e)}"
        )


@router.delete("/modules/{module_id}")
async def delete_module(module_id: str):
    """Delete a module."""
    try:
        module = await Module.get(module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        await module.delete()

        return {"message": "Module deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting module {module_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting module: {str(e)}"
        )


@router.post("/modules/{module_id}/generate-overview", response_model=ModuleResponse)
async def generate_module_overview(
    module_id: str, request: Optional[GenerateOverviewRequest] = None
):
    """Generate an AI overview for a module based on its sources and notes."""
    try:
        # Get the module
        module = await Module.get(module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        # Get sources and notes for context
        sources = await module.get_sources()
        notes = await module.get_notes()

        # Build context for prompt
        sources_context = []
        for source in sources:
            source_data = {
                "title": source.title,
                "full_text": source.full_text,
                "insights": [],
            }
            try:
                insights = await source.get_insights()
                for insight in insights:
                    source_data["insights"].append({
                        "insight_type": insight.insight_type,
                        "content": insight.content,
                    })
            except Exception as e:
                logger.warning(f"Error getting insights for source {source.id}: {e}")
            sources_context.append(source_data)

        notes_context = []
        for note in notes:
            notes_context.append({
                "title": note.title,
                "content": note.content,
            })

        # Render prompt
        prompt_data = {
            "name": module.name,
            "description": module.description,
            "sources": sources_context,
            "notes": notes_context,
        }
        system_prompt = Prompter(prompt_template="module/overview").render(
            data=prompt_data
        )

        # Get model ID from request or use default
        model_id = request.model_id if request else None

        # Provision and invoke LLM
        model = await provision_langchain_model(
            system_prompt,
            model_id,
            "transformation",
            max_tokens=2000,
        )
        ai_message = await model.ainvoke(system_prompt)

        # Extract content
        overview_content = (
            ai_message.content
            if isinstance(ai_message.content, str)
            else str(ai_message.content)
        )
        overview_content = clean_thinking_content(overview_content)

        # Save the overview to the module
        module.overview = overview_content
        await module.save()

        # Return updated module
        query = """
            SELECT *,
            count(<-reference.in) as source_count,
            count(<-artifact.in) as note_count
            FROM $module_id
        """
        result = await repo_query(query, {"module_id": ensure_record_id(module_id)})

        if result:
            nb = result[0]
            return ModuleResponse(
                id=str(nb.get("id", "")),
                name=nb.get("name", ""),
                description=nb.get("description", ""),
                archived=nb.get("archived", False),
                overview=nb.get("overview"),
                created=str(nb.get("created", "")),
                updated=str(nb.get("updated", "")),
                source_count=nb.get("source_count", 0),
                note_count=nb.get("note_count", 0),
            )

        # Fallback
        return ModuleResponse(
            id=module.id or "",
            name=module.name,
            description=module.description,
            archived=module.archived or False,
            overview=module.overview,
            created=str(module.created),
            updated=str(module.updated),
            source_count=0,
            note_count=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating overview for module {module_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generating overview: {str(e)}"
        )
