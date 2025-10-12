import time
from typing import Dict, List, Literal, Optional

from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.models import model_manager
from open_notebook.domain.notebook import Note, Source, SourceInsight


def full_model_dump(model):
    if isinstance(model, BaseModel):
        return model.model_dump()
    elif isinstance(model, dict):
        return {k: full_model_dump(v) for k, v in model.items()}
    elif isinstance(model, list):
        return [full_model_dump(item) for item in model]
    else:
        return model


class EmbedSingleItemInput(CommandInput):
    item_id: str
    item_type: Literal["source", "note", "insight"]


class EmbedSingleItemOutput(CommandOutput):
    success: bool
    item_id: str
    item_type: str
    chunks_created: int = 0  # For sources
    processing_time: float
    error_message: Optional[str] = None


class RebuildEmbeddingsInput(CommandInput):
    mode: Literal["existing", "all"]
    include_sources: bool = True
    include_notes: bool = True
    include_insights: bool = True


class RebuildEmbeddingsOutput(CommandOutput):
    success: bool
    total_items: int
    processed_items: int
    failed_items: int
    sources_processed: int = 0
    notes_processed: int = 0
    insights_processed: int = 0
    processing_time: float
    error_message: Optional[str] = None


@command("embed_single_item", app="open_notebook")
async def embed_single_item_command(
    input_data: EmbedSingleItemInput,
) -> EmbedSingleItemOutput:
    """
    Embed a single item (source, note, or insight)
    """
    start_time = time.time()

    try:
        logger.info(
            f"Starting embedding for {input_data.item_type}: {input_data.item_id}"
        )

        # Check if embedding model is available
        EMBEDDING_MODEL = await model_manager.get_embedding_model()
        if not EMBEDDING_MODEL:
            raise ValueError(
                "No embedding model configured. Please configure one in the Models section."
            )

        chunks_created = 0

        if input_data.item_type == "source":
            # Get source and vectorize
            source = await Source.get(input_data.item_id)
            if not source:
                raise ValueError(f"Source '{input_data.item_id}' not found")

            await source.vectorize()

            # Count chunks created
            chunks_result = await repo_query(
                "SELECT VALUE count() FROM source_embedding WHERE source = $source_id GROUP ALL",
                {"source_id": ensure_record_id(input_data.item_id)},
            )
            if chunks_result and isinstance(chunks_result[0], dict):
                chunks_created = chunks_result[0].get("count", 0)
            elif chunks_result and isinstance(chunks_result[0], int):
                chunks_created = chunks_result[0]
            else:
                chunks_created = 0

            logger.info(f"Source vectorized: {chunks_created} chunks created")

        elif input_data.item_type == "note":
            # Get note and save (auto-embeds via ObjectModel.save())
            note = await Note.get(input_data.item_id)
            if not note:
                raise ValueError(f"Note '{input_data.item_id}' not found")

            await note.save()
            logger.info(f"Note embedded: {input_data.item_id}")

        elif input_data.item_type == "insight":
            # Get insight and re-generate embedding
            insight = await SourceInsight.get(input_data.item_id)
            if not insight:
                raise ValueError(f"Insight '{input_data.item_id}' not found")

            # Generate new embedding
            embedding = (await EMBEDDING_MODEL.aembed([insight.content]))[0]

            # Update insight with new embedding
            await repo_query(
                "UPDATE $insight_id SET embedding = $embedding",
                {
                    "insight_id": ensure_record_id(input_data.item_id),
                    "embedding": embedding,
                },
            )
            logger.info(f"Insight embedded: {input_data.item_id}")

        else:
            raise ValueError(
                f"Invalid item_type: {input_data.item_type}. Must be 'source', 'note', or 'insight'"
            )

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully embedded {input_data.item_type} {input_data.item_id} in {processing_time:.2f}s"
        )

        return EmbedSingleItemOutput(
            success=True,
            item_id=input_data.item_id,
            item_type=input_data.item_type,
            chunks_created=chunks_created,
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Embedding failed for {input_data.item_type} {input_data.item_id}: {e}")
        logger.exception(e)

        return EmbedSingleItemOutput(
            success=False,
            item_id=input_data.item_id,
            item_type=input_data.item_type,
            processing_time=processing_time,
            error_message=str(e),
        )


async def collect_items_for_rebuild(
    mode: str,
    include_sources: bool,
    include_notes: bool,
    include_insights: bool,
) -> Dict[str, List[str]]:
    """
    Collect items to rebuild based on mode and include flags.

    Returns:
        Dict with keys: 'sources', 'notes', 'insights' containing lists of item IDs
    """
    items: Dict[str, List[str]] = {"sources": [], "notes": [], "insights": []}

    if include_sources:
        if mode == "existing":
            # Query sources with embeddings (via source_embedding table)
            result = await repo_query(
                """
                RETURN array::distinct(
                    SELECT VALUE source.id
                    FROM source_embedding
                    WHERE embedding != none AND array::len(embedding) > 0
                )
                """
            )
            # RETURN returns the array directly as the result (not nested)
            if result:
                items["sources"] = [str(item) for item in result]
            else:
                items["sources"] = []
        else:  # mode == "all"
            # Query all sources with content
            result = await repo_query("SELECT id FROM source WHERE full_text != none")
            items["sources"] = [str(item["id"]) for item in result] if result else []

        logger.info(f"Collected {len(items['sources'])} sources for rebuild")

    if include_notes:
        if mode == "existing":
            # Query notes with embeddings
            result = await repo_query(
                "SELECT id FROM note WHERE embedding != none AND array::len(embedding) > 0"
            )
        else:  # mode == "all"
            # Query all notes (with content)
            result = await repo_query("SELECT id FROM note WHERE content != none")

        items["notes"] = [str(item["id"]) for item in result] if result else []
        logger.info(f"Collected {len(items['notes'])} notes for rebuild")

    if include_insights:
        if mode == "existing":
            # Query insights with embeddings
            result = await repo_query(
                "SELECT id FROM source_insight WHERE embedding != none AND array::len(embedding) > 0"
            )
        else:  # mode == "all"
            # Query all insights
            result = await repo_query("SELECT id FROM source_insight")

        items["insights"] = [str(item["id"]) for item in result] if result else []
        logger.info(f"Collected {len(items['insights'])} insights for rebuild")

    return items


@command("rebuild_embeddings", app="open_notebook")
async def rebuild_embeddings_command(
    input_data: RebuildEmbeddingsInput,
) -> RebuildEmbeddingsOutput:
    """
    Rebuild embeddings for sources, notes, and/or insights
    """
    start_time = time.time()

    try:
        logger.info("=" * 60)
        logger.info(f"Starting embedding rebuild with mode={input_data.mode}")
        logger.info(f"Include: sources={input_data.include_sources}, notes={input_data.include_notes}, insights={input_data.include_insights}")
        logger.info("=" * 60)

        # Check embedding model availability
        EMBEDDING_MODEL = await model_manager.get_embedding_model()
        if not EMBEDDING_MODEL:
            raise ValueError(
                "No embedding model configured. Please configure one in the Models section."
            )

        logger.info(f"Using embedding model: {EMBEDDING_MODEL}")

        # Collect items to process
        items = await collect_items_for_rebuild(
            input_data.mode,
            input_data.include_sources,
            input_data.include_notes,
            input_data.include_insights,
        )

        total_items = (
            len(items["sources"]) + len(items["notes"]) + len(items["insights"])
        )
        logger.info(f"Total items to process: {total_items}")

        if total_items == 0:
            logger.warning("No items found to rebuild")
            return RebuildEmbeddingsOutput(
                success=True,
                total_items=0,
                processed_items=0,
                failed_items=0,
                processing_time=time.time() - start_time,
            )

        # Initialize counters
        sources_processed = 0
        notes_processed = 0
        insights_processed = 0
        failed_items = 0

        # Process sources
        logger.info(f"\nProcessing {len(items['sources'])} sources...")
        for idx, source_id in enumerate(items["sources"], 1):
            try:
                source = await Source.get(source_id)
                if not source:
                    logger.warning(f"Source {source_id} not found, skipping")
                    failed_items += 1
                    continue

                await source.vectorize()
                sources_processed += 1

                if idx % 10 == 0 or idx == len(items["sources"]):
                    logger.info(
                        f"  Progress: {idx}/{len(items['sources'])} sources processed"
                    )

            except Exception as e:
                logger.error(f"Failed to re-embed source {source_id}: {e}")
                failed_items += 1

        # Process notes
        logger.info(f"\nProcessing {len(items['notes'])} notes...")
        for idx, note_id in enumerate(items["notes"], 1):
            try:
                note = await Note.get(note_id)
                if not note:
                    logger.warning(f"Note {note_id} not found, skipping")
                    failed_items += 1
                    continue

                await note.save()  # Auto-embeds via ObjectModel.save()
                notes_processed += 1

                if idx % 10 == 0 or idx == len(items["notes"]):
                    logger.info(f"  Progress: {idx}/{len(items['notes'])} notes processed")

            except Exception as e:
                logger.error(f"Failed to re-embed note {note_id}: {e}")
                failed_items += 1

        # Process insights
        logger.info(f"\nProcessing {len(items['insights'])} insights...")
        for idx, insight_id in enumerate(items["insights"], 1):
            try:
                insight = await SourceInsight.get(insight_id)
                if not insight:
                    logger.warning(f"Insight {insight_id} not found, skipping")
                    failed_items += 1
                    continue

                # Re-generate embedding
                embedding = (await EMBEDDING_MODEL.aembed([insight.content]))[0]

                # Update insight with new embedding
                await repo_query(
                    "UPDATE $insight_id SET embedding = $embedding",
                    {
                        "insight_id": ensure_record_id(insight_id),
                        "embedding": embedding,
                    },
                )
                insights_processed += 1

                if idx % 10 == 0 or idx == len(items["insights"]):
                    logger.info(
                        f"  Progress: {idx}/{len(items['insights'])} insights processed"
                    )

            except Exception as e:
                logger.error(f"Failed to re-embed insight {insight_id}: {e}")
                failed_items += 1

        processing_time = time.time() - start_time
        processed_items = sources_processed + notes_processed + insights_processed

        logger.info("=" * 60)
        logger.info("REBUILD COMPLETE")
        logger.info(f"  Total processed: {processed_items}/{total_items}")
        logger.info(f"  Sources: {sources_processed}")
        logger.info(f"  Notes: {notes_processed}")
        logger.info(f"  Insights: {insights_processed}")
        logger.info(f"  Failed: {failed_items}")
        logger.info(f"  Time: {processing_time:.2f}s")
        logger.info("=" * 60)

        return RebuildEmbeddingsOutput(
            success=True,
            total_items=total_items,
            processed_items=processed_items,
            failed_items=failed_items,
            sources_processed=sources_processed,
            notes_processed=notes_processed,
            insights_processed=insights_processed,
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Rebuild embeddings failed: {e}")
        logger.exception(e)

        return RebuildEmbeddingsOutput(
            success=False,
            total_items=0,
            processed_items=0,
            failed_items=0,
            processing_time=processing_time,
            error_message=str(e),
        )
