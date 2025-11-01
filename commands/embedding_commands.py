import time
from typing import Dict, List, Literal, Optional

from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command, submit_command

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.models import model_manager
from open_notebook.domain.notebook import Note, Source, SourceInsight
from open_notebook.utils.text_utils import split_text


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


class EmbedChunkInput(CommandInput):
    source_id: str
    chunk_index: int
    chunk_text: str


class EmbedChunkOutput(CommandOutput):
    success: bool
    source_id: str
    chunk_index: int
    error_message: Optional[str] = None


class VectorizeSourceInput(CommandInput):
    source_id: str


class VectorizeSourceOutput(CommandOutput):
    success: bool
    source_id: str
    total_chunks: int
    jobs_submitted: int
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


@command(
    "embed_chunk",
    app="open_notebook",
    retry={
        "max_attempts": 5,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 30,
        "retry_on": [RuntimeError, ConnectionError, TimeoutError],
    },
)
async def embed_chunk_command(
    input_data: EmbedChunkInput,
) -> EmbedChunkOutput:
    """
    Process a single text chunk for embedding as part of source vectorization.

    This command is designed to be submitted as a background job for each chunk
    of a source document, allowing natural concurrency control through the worker pool.

    Retry Strategy:
    - Retries up to 5 times for transient failures:
      * RuntimeError: SurrealDB transaction conflicts ("read or write conflict")
      * ConnectionError: Network failures when calling embedding provider
      * TimeoutError: Request timeouts to embedding provider
    - Uses exponential-jitter backoff (1-30s) to prevent thundering herd during concurrent operations
    - Does NOT retry permanent failures (ValueError, authentication errors, invalid input)

    Exception Handling:
    - RuntimeError, ConnectionError, TimeoutError: Re-raised to trigger retry mechanism
    - ValueError and other exceptions: Caught and returned as permanent failures (no retry)
    """
    try:
        logger.debug(
            f"Processing chunk {input_data.chunk_index} for source {input_data.source_id}"
        )

        # Get embedding model
        EMBEDDING_MODEL = await model_manager.get_embedding_model()
        if not EMBEDDING_MODEL:
            raise ValueError(
                "No embedding model configured. Please configure one in the Models section."
            )

        # Generate embedding for the chunk
        embedding = (await EMBEDDING_MODEL.aembed([input_data.chunk_text]))[0]

        # Insert chunk embedding into database
        await repo_query(
            """
            CREATE source_embedding CONTENT {
                "source": $source_id,
                "order": $order,
                "content": $content,
                "embedding": $embedding,
            };
            """,
            {
                "source_id": ensure_record_id(input_data.source_id),
                "order": input_data.chunk_index,
                "content": input_data.chunk_text,
                "embedding": embedding,
            },
        )

        logger.debug(
            f"Successfully embedded chunk {input_data.chunk_index} for source {input_data.source_id}"
        )

        return EmbedChunkOutput(
            success=True,
            source_id=input_data.source_id,
            chunk_index=input_data.chunk_index,
        )

    except RuntimeError:
        # Re-raise RuntimeError to allow retry mechanism to handle DB transaction conflicts
        logger.warning(
            f"Transaction conflict for chunk {input_data.chunk_index} - will be retried by retry mechanism"
        )
        raise
    except (ConnectionError, TimeoutError) as e:
        # Re-raise network/timeout errors to allow retry mechanism to handle transient provider failures
        logger.warning(
            f"Network/timeout error for chunk {input_data.chunk_index} ({type(e).__name__}: {e}) - will be retried by retry mechanism"
        )
        raise
    except Exception as e:
        # Catch other exceptions (ValueError, etc.) as permanent failures
        logger.error(
            f"Failed to embed chunk {input_data.chunk_index} for source {input_data.source_id}: {e}"
        )
        logger.exception(e)

        return EmbedChunkOutput(
            success=False,
            source_id=input_data.source_id,
            chunk_index=input_data.chunk_index,
            error_message=str(e),
        )


@command("vectorize_source", app="open_notebook", retry=None)
async def vectorize_source_command(
    input_data: VectorizeSourceInput,
) -> VectorizeSourceOutput:
    """
    Orchestrate source vectorization by splitting text into chunks and submitting
    individual embed_chunk jobs to the worker queue.

    This command:
    1. Deletes existing embeddings (idempotency)
    2. Splits source text into chunks
    3. Submits each chunk as a separate embed_chunk job
    4. Returns immediately (jobs run in background)

    Natural concurrency control is provided by the worker pool size.

    Retry Strategy:
    - Retries disabled (retry=None) - fails fast on job submission errors
    - This ensures immediate visibility when orchestration fails
    - Individual embed_chunk jobs have their own retry logic for DB conflicts
    """
    start_time = time.time()

    try:
        logger.info(f"Starting vectorization orchestration for source {input_data.source_id}")

        # 1. Load source
        source = await Source.get(input_data.source_id)
        if not source:
            raise ValueError(f"Source '{input_data.source_id}' not found")

        if not source.full_text:
            raise ValueError(f"Source {input_data.source_id} has no text to vectorize")

        # 2. Delete existing embeddings (idempotency)
        logger.info(f"Deleting existing embeddings for source {input_data.source_id}")
        delete_result = await repo_query(
            "DELETE source_embedding WHERE source = $source_id",
            {"source_id": ensure_record_id(input_data.source_id)}
        )
        deleted_count = len(delete_result) if delete_result else 0
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} existing embeddings")

        # 3. Split text into chunks
        logger.info(f"Splitting text into chunks for source {input_data.source_id}")
        chunks = split_text(source.full_text)
        total_chunks = len(chunks)
        logger.info(f"Split into {total_chunks} chunks")

        if total_chunks == 0:
            raise ValueError("No chunks created after splitting text")

        # 4. Submit each chunk as a separate job
        logger.info(f"Submitting {total_chunks} chunk jobs to worker queue")
        jobs_submitted = 0

        for idx, chunk_text in enumerate(chunks):
            try:
                job_id = submit_command(
                    "open_notebook",  # app name
                    "embed_chunk",    # command name
                    {
                        "source_id": input_data.source_id,
                        "chunk_index": idx,
                        "chunk_text": chunk_text,
                    }
                )
                jobs_submitted += 1

                if (idx + 1) % 100 == 0:
                    logger.info(f"  Submitted {idx + 1}/{total_chunks} chunk jobs")

            except Exception as e:
                logger.error(f"Failed to submit chunk job {idx}: {e}")
                # Continue submitting other chunks even if one fails

        processing_time = time.time() - start_time

        logger.info(
            f"Vectorization orchestration complete for source {input_data.source_id}: "
            f"{jobs_submitted}/{total_chunks} jobs submitted in {processing_time:.2f}s"
        )

        return VectorizeSourceOutput(
            success=True,
            source_id=input_data.source_id,
            total_chunks=total_chunks,
            jobs_submitted=jobs_submitted,
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Vectorization orchestration failed for source {input_data.source_id}: {e}")
        logger.exception(e)

        return VectorizeSourceOutput(
            success=False,
            source_id=input_data.source_id,
            total_chunks=0,
            jobs_submitted=0,
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


@command("rebuild_embeddings", app="open_notebook", retry=None)
async def rebuild_embeddings_command(
    input_data: RebuildEmbeddingsInput,
) -> RebuildEmbeddingsOutput:
    """
    Rebuild embeddings for sources, notes, and/or insights

    Retry Strategy:
    - Retries disabled (retry=None) - batch failures are immediately reported
    - This ensures immediate visibility when batch operations fail
    - Allows operators to quickly identify and resolve issues
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
