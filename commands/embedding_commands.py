import time
from typing import Dict, List, Literal, Optional

from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command, submit_command

from open_notebook.ai.models import model_manager
from open_notebook.database.repository import ensure_record_id, repo_insert, repo_query
from open_notebook.domain.notebook import Note, Source, SourceInsight
from open_notebook.utils.chunking import ContentType, chunk_text, detect_content_type
from open_notebook.utils.embedding import generate_embedding, generate_embeddings


def full_model_dump(model):
    if isinstance(model, BaseModel):
        return model.model_dump()
    elif isinstance(model, dict):
        return {k: full_model_dump(v) for k, v in model.items()}
    elif isinstance(model, list):
        return [full_model_dump(item) for item in model]
    else:
        return model


def get_command_id(input_data: CommandInput) -> str:
    """Extract command_id from input_data's execution context, or return 'unknown'."""
    if input_data.execution_context:
        return str(input_data.execution_context.command_id)
    return "unknown"


class RebuildEmbeddingsInput(CommandInput):
    mode: Literal["existing", "all"]
    include_sources: bool = True
    include_notes: bool = True
    include_insights: bool = True


class RebuildEmbeddingsOutput(CommandOutput):
    success: bool
    total_items: int
    jobs_submitted: int  # Count of embedding commands submitted
    failed_submissions: int  # Count of items that failed to submit
    sources_submitted: int = 0
    notes_submitted: int = 0
    insights_submitted: int = 0
    processing_time: float
    error_message: Optional[str] = None


# =============================================================================
# NEW EMBEDDING COMMANDS (Phase 3)
# =============================================================================


class CreateInsightInput(CommandInput):
    """Input for creating a source insight with automatic retry on conflicts."""

    source_id: str
    insight_type: str
    content: str


class CreateInsightOutput(CommandOutput):
    """Output from insight creation command."""

    success: bool
    insight_id: Optional[str] = None
    processing_time: float
    error_message: Optional[str] = None


class EmbedNoteInput(CommandInput):
    """Input for embedding a single note."""

    note_id: str


class EmbedNoteOutput(CommandOutput):
    """Output from note embedding command."""

    success: bool
    note_id: str
    processing_time: float
    error_message: Optional[str] = None


class EmbedInsightInput(CommandInput):
    """Input for embedding a single source insight."""

    insight_id: str


class EmbedInsightOutput(CommandOutput):
    """Output from insight embedding command."""

    success: bool
    insight_id: str
    processing_time: float
    error_message: Optional[str] = None


class EmbedSourceInput(CommandInput):
    """Input for embedding a source (creates multiple chunk embeddings)."""

    source_id: str


class EmbedSourceOutput(CommandOutput):
    """Output from source embedding command."""

    success: bool
    source_id: str
    chunks_created: int
    processing_time: float
    error_message: Optional[str] = None


@command(
    "embed_note",
    app="open_notebook",
    retry={
        "max_attempts": 5,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 60,
        "stop_on": [ValueError],  # Don't retry validation errors
        "retry_log_level": "debug",
    },
)
async def embed_note_command(input_data: EmbedNoteInput) -> EmbedNoteOutput:
    """
    Generate and store embedding for a single note.

    Uses the unified embedding pipeline with automatic chunking and mean pooling
    for notes that exceed the chunk size limit.

    Flow:
    1. Load Note by ID
    2. Generate embedding via generate_embedding() (auto-chunks + mean pools if needed)
    3. UPSERT note embedding in database

    Retry Strategy:
    - Retries up to 5 times for transient failures (network, timeout, etc.)
    - Uses exponential-jitter backoff (1-60s)
    - Does NOT retry permanent failures (ValueError for validation errors)
    """
    start_time = time.time()

    try:
        logger.info(f"Starting embedding for note: {input_data.note_id}")

        # 1. Load note
        note = await Note.get(input_data.note_id)
        if not note:
            raise ValueError(f"Note '{input_data.note_id}' not found")

        if not note.content or not note.content.strip():
            raise ValueError(f"Note '{input_data.note_id}' has no content to embed")

        # 2. Generate embedding (auto-chunks + mean pools if needed)
        # Notes are typically markdown content
        cmd_id = get_command_id(input_data)
        embedding = await generate_embedding(
            note.content, content_type=ContentType.MARKDOWN, command_id=cmd_id
        )

        # 3. UPSERT embedding into note record
        await repo_query(
            "UPDATE $note_id SET embedding = $embedding",
            {
                "note_id": ensure_record_id(input_data.note_id),
                "embedding": embedding,
            },
        )

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully embedded note {input_data.note_id} in {processing_time:.2f}s"
        )

        return EmbedNoteOutput(
            success=True,
            note_id=input_data.note_id,
            processing_time=processing_time,
        )

    except ValueError as e:
        # Permanent failure - don't retry
        processing_time = time.time() - start_time
        cmd_id = get_command_id(input_data)
        logger.error(
            f"Failed to embed note {input_data.note_id} (command: {cmd_id}): {e}"
        )
        return EmbedNoteOutput(
            success=False,
            note_id=input_data.note_id,
            processing_time=processing_time,
            error_message=str(e),
        )
    except Exception as e:
        # Transient failure - will be retried (surreal-commands logs final failure)
        cmd_id = get_command_id(input_data)
        logger.debug(
            f"Transient error embedding note {input_data.note_id} "
            f"(command: {cmd_id}): {e}"
        )
        raise


@command(
    "embed_insight",
    app="open_notebook",
    retry={
        "max_attempts": 5,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 60,
        "stop_on": [ValueError],  # Don't retry validation errors
        "retry_log_level": "debug",
    },
)
async def embed_insight_command(input_data: EmbedInsightInput) -> EmbedInsightOutput:
    """
    Generate and store embedding for a single source insight.

    Uses the unified embedding pipeline with automatic chunking and mean pooling
    for insights that exceed the chunk size limit.

    Flow:
    1. Load SourceInsight by ID
    2. Generate embedding via generate_embedding() (auto-chunks + mean pools if needed)
    3. UPSERT insight embedding in database

    Retry Strategy:
    - Retries up to 5 times for transient failures (network, timeout, etc.)
    - Uses exponential-jitter backoff (1-60s)
    - Does NOT retry permanent failures (ValueError for validation errors)
    """
    start_time = time.time()

    try:
        logger.info(f"Starting embedding for insight: {input_data.insight_id}")

        # 1. Load insight
        insight = await SourceInsight.get(input_data.insight_id)
        if not insight:
            raise ValueError(f"Insight '{input_data.insight_id}' not found")

        if not insight.content or not insight.content.strip():
            raise ValueError(
                f"Insight '{input_data.insight_id}' has no content to embed"
            )

        # 2. Generate embedding (auto-chunks + mean pools if needed)
        # Insights are typically markdown content (generated by LLM)
        cmd_id = get_command_id(input_data)
        embedding = await generate_embedding(
            insight.content, content_type=ContentType.MARKDOWN, command_id=cmd_id
        )

        # 3. UPSERT embedding into insight record
        await repo_query(
            "UPDATE $insight_id SET embedding = $embedding",
            {
                "insight_id": ensure_record_id(input_data.insight_id),
                "embedding": embedding,
            },
        )

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully embedded insight {input_data.insight_id} in {processing_time:.2f}s"
        )

        return EmbedInsightOutput(
            success=True,
            insight_id=input_data.insight_id,
            processing_time=processing_time,
        )

    except ValueError as e:
        # Permanent failure - don't retry
        processing_time = time.time() - start_time
        cmd_id = get_command_id(input_data)
        logger.error(
            f"Failed to embed insight {input_data.insight_id} (command: {cmd_id}): {e}"
        )
        return EmbedInsightOutput(
            success=False,
            insight_id=input_data.insight_id,
            processing_time=processing_time,
            error_message=str(e),
        )
    except Exception as e:
        # Transient failure - will be retried (surreal-commands logs final failure)
        cmd_id = get_command_id(input_data)
        logger.debug(
            f"Transient error embedding insight {input_data.insight_id} "
            f"(command: {cmd_id}): {e}"
        )
        raise


@command(
    "embed_source",
    app="open_notebook",
    retry={
        "max_attempts": 5,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 60,
        "stop_on": [ValueError],  # Don't retry validation errors
        "retry_log_level": "debug",
    },
)
async def embed_source_command(input_data: EmbedSourceInput) -> EmbedSourceOutput:
    """
    Generate and store embeddings for a source document.

    Creates multiple chunk embeddings stored in the source_embedding table.
    Uses content-type aware chunking based on file extension or content heuristics.

    Flow:
    1. Load Source by ID
    2. DELETE existing source_embedding records for this source
    3. Detect content type from file path or content
    4. Chunk text using appropriate splitter
    5. Generate embeddings for all chunks in a single API call
    6. Bulk INSERT source_embedding records

    Retry Strategy:
    - Retries up to 5 times for transient failures (network, timeout, etc.)
    - Uses exponential-jitter backoff (1-60s)
    - Does NOT retry permanent failures (ValueError for validation errors)
    """
    start_time = time.time()

    try:
        logger.info(f"Starting embedding for source: {input_data.source_id}")

        # 1. Load source
        source = await Source.get(input_data.source_id)
        if not source:
            raise ValueError(f"Source '{input_data.source_id}' not found")

        if not source.full_text or not source.full_text.strip():
            raise ValueError(f"Source '{input_data.source_id}' has no text to embed")

        # 2. DELETE existing embeddings (idempotency)
        logger.debug(f"Deleting existing embeddings for source {input_data.source_id}")
        await repo_query(
            "DELETE source_embedding WHERE source = $source_id",
            {"source_id": ensure_record_id(input_data.source_id)},
        )

        # 3. Detect content type from file path if available
        file_path = source.asset.file_path if source.asset else None
        content_type = detect_content_type(source.full_text, file_path)
        logger.debug(f"Detected content type: {content_type.value}")

        # 4. Chunk text using appropriate splitter
        chunks = chunk_text(source.full_text, content_type=content_type)
        total_chunks = len(chunks)

        # Log chunk statistics for debugging
        chunk_sizes = [len(c) for c in chunks]
        logger.info(
            f"Created {total_chunks} chunks for source {input_data.source_id} "
            f"(sizes: min={min(chunk_sizes) if chunk_sizes else 0}, "
            f"max={max(chunk_sizes) if chunk_sizes else 0}, "
            f"avg={sum(chunk_sizes)//len(chunk_sizes) if chunk_sizes else 0} chars)"
        )

        if total_chunks == 0:
            raise ValueError("No chunks created after splitting text")

        # 5. Generate embeddings for all chunks in single API call
        cmd_id = get_command_id(input_data)
        logger.debug(f"Generating embeddings for {total_chunks} chunks")
        embeddings = await generate_embeddings(chunks, command_id=cmd_id)

        # Verify we got embeddings for all chunks
        if len(embeddings) != len(chunks):
            raise ValueError(
                f"Embedding count mismatch: got {len(embeddings)} embeddings "
                f"for {len(chunks)} chunks"
            )

        # 6. Bulk INSERT source_embedding records
        records = [
            {
                "source": ensure_record_id(input_data.source_id),
                "order": idx,
                "content": chunk,
                "embedding": embedding,
            }
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        logger.debug(f"Inserting {len(records)} source_embedding records")
        await repo_insert("source_embedding", records)

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully embedded source {input_data.source_id}: "
            f"{total_chunks} chunks in {processing_time:.2f}s"
        )

        return EmbedSourceOutput(
            success=True,
            source_id=input_data.source_id,
            chunks_created=total_chunks,
            processing_time=processing_time,
        )

    except ValueError as e:
        # Permanent failure - don't retry
        processing_time = time.time() - start_time
        cmd_id = get_command_id(input_data)
        logger.error(
            f"Failed to embed source {input_data.source_id} (command: {cmd_id}): {e}"
        )
        return EmbedSourceOutput(
            success=False,
            source_id=input_data.source_id,
            chunks_created=0,
            processing_time=processing_time,
            error_message=str(e),
        )
    except Exception as e:
        # Transient failure - will be retried (surreal-commands logs final failure)
        cmd_id = get_command_id(input_data)
        logger.debug(
            f"Transient error embedding source {input_data.source_id} "
            f"(command: {cmd_id}): {e}"
        )
        raise


@command(
    "create_insight",
    app="open_notebook",
    retry={
        "max_attempts": 5,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 60,
        "stop_on": [ValueError],  # Don't retry validation errors
        "retry_log_level": "debug",
    },
)
async def create_insight_command(
    input_data: CreateInsightInput,
) -> CreateInsightOutput:
    """
    Create a source insight with automatic retry on transaction conflicts.

    This command wraps the CREATE source_insight operation with retry logic
    to handle SurrealDB transaction conflicts that occur during batch imports
    when multiple parallel transformations try to create insights concurrently.

    Flow:
    1. CREATE source_insight record in database
    2. Submit embed_insight command (fire-and-forget) for async embedding
    3. Return the insight_id

    Retry Strategy:
    - Retries up to 5 times for transient failures (network, timeout, etc.)
    - Uses exponential-jitter backoff (1-60s)
    - Does NOT retry permanent failures (ValueError for validation errors)
    """
    start_time = time.time()

    try:
        logger.info(
            f"Creating insight for source {input_data.source_id}: "
            f"type={input_data.insight_type}"
        )

        # 1. Create insight record in database
        result = await repo_query(
            """
            CREATE source_insight CONTENT {
                "source": $source_id,
                "insight_type": $insight_type,
                "content": $content
            };
            """,
            {
                "source_id": ensure_record_id(input_data.source_id),
                "insight_type": input_data.insight_type,
                "content": input_data.content,
            },
        )

        if not result or len(result) == 0:
            raise ValueError("Failed to create insight - no result returned")

        insight_id = str(result[0].get("id", ""))
        if not insight_id:
            raise ValueError("Failed to create insight - no ID in result")

        # 2. Submit embedding command (fire-and-forget)
        submit_command(
            "open_notebook",
            "embed_insight",
            {"insight_id": insight_id},
        )
        logger.debug(f"Submitted embed_insight command for {insight_id}")

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully created insight {insight_id} for source "
            f"{input_data.source_id} in {processing_time:.2f}s"
        )

        return CreateInsightOutput(
            success=True,
            insight_id=insight_id,
            processing_time=processing_time,
        )

    except ValueError as e:
        # Permanent failure - don't retry
        processing_time = time.time() - start_time
        cmd_id = get_command_id(input_data)
        logger.error(
            f"Failed to create insight for source {input_data.source_id} "
            f"(command: {cmd_id}): {e}"
        )
        return CreateInsightOutput(
            success=False,
            processing_time=processing_time,
            error_message=str(e),
        )
    except Exception as e:
        # Transient failure - will be retried (surreal-commands logs final failure)
        cmd_id = get_command_id(input_data)
        logger.debug(
            f"Transient error creating insight for source {input_data.source_id} "
            f"(command: {cmd_id}): {e}"
        )
        raise


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
            # Query all sources with non-empty content
            result = await repo_query(
                "SELECT id FROM source WHERE full_text != none AND string::trim(full_text) != ''"
            )
            items["sources"] = [str(item["id"]) for item in result] if result else []

        logger.info(f"Collected {len(items['sources'])} sources for rebuild")

    if include_notes:
        if mode == "existing":
            # Query notes with embeddings
            result = await repo_query(
                "SELECT id FROM note WHERE embedding != none AND array::len(embedding) > 0"
            )
        else:  # mode == "all"
            # Query all notes with non-empty content
            result = await repo_query(
                "SELECT id FROM note WHERE content != none AND string::trim(content) != ''"
            )

        items["notes"] = [str(item["id"]) for item in result] if result else []
        logger.info(f"Collected {len(items['notes'])} notes for rebuild")

    if include_insights:
        if mode == "existing":
            # Query insights with embeddings
            result = await repo_query(
                "SELECT id FROM source_insight WHERE embedding != none AND array::len(embedding) > 0"
            )
        else:  # mode == "all"
            # Query all insights with non-empty content
            result = await repo_query(
                "SELECT id FROM source_insight WHERE content != none AND string::trim(content) != ''"
            )

        items["insights"] = [str(item["id"]) for item in result] if result else []
        logger.info(f"Collected {len(items['insights'])} insights for rebuild")

    return items


@command("rebuild_embeddings", app="open_notebook", retry=None)
async def rebuild_embeddings_command(
    input_data: RebuildEmbeddingsInput,
) -> RebuildEmbeddingsOutput:
    """
    Rebuild embeddings for sources, notes, and/or insights.

    This command submits individual embedding jobs for each item:
    - embed_source for sources
    - embed_note for notes
    - embed_insight for insights

    The command returns after submitting all jobs. Actual embedding
    happens asynchronously via the individual commands (which have
    their own retry strategies).

    Retry Strategy:
    - Retries disabled (retry=None) for this coordinator command
    - Individual embed_* commands handle their own retries
    """
    start_time = time.time()

    try:
        logger.info("=" * 60)
        logger.info(f"Starting embedding rebuild with mode={input_data.mode}")
        logger.info(
            f"Include: sources={input_data.include_sources}, notes={input_data.include_notes}, insights={input_data.include_insights}"
        )
        logger.info("=" * 60)

        # Check embedding model availability (fail fast)
        EMBEDDING_MODEL = await model_manager.get_embedding_model()
        if not EMBEDDING_MODEL:
            raise ValueError(
                "No embedding model configured. Please configure one in the Models section."
            )

        logger.info(f"Embedding model configured: {EMBEDDING_MODEL}")

        # Collect items to process (returns IDs only)
        items = await collect_items_for_rebuild(
            input_data.mode,
            input_data.include_sources,
            input_data.include_notes,
            input_data.include_insights,
        )

        total_items = (
            len(items["sources"]) + len(items["notes"]) + len(items["insights"])
        )
        logger.info(f"Total items to rebuild: {total_items}")

        if total_items == 0:
            logger.warning("No items found to rebuild")
            return RebuildEmbeddingsOutput(
                success=True,
                total_items=0,
                jobs_submitted=0,
                failed_submissions=0,
                processing_time=time.time() - start_time,
            )

        # Initialize counters
        sources_submitted = 0
        notes_submitted = 0
        insights_submitted = 0
        failed_submissions = 0

        # Submit embed_source commands for sources
        logger.info(f"\nSubmitting {len(items['sources'])} source embedding jobs...")
        for idx, source_id in enumerate(items["sources"], 1):
            try:
                submit_command(
                    "open_notebook",
                    "embed_source",
                    {"source_id": source_id},
                )
                sources_submitted += 1

                if idx % 50 == 0 or idx == len(items["sources"]):
                    logger.info(
                        f"  Progress: {idx}/{len(items['sources'])} source jobs submitted"
                    )

            except Exception as e:
                logger.error(f"Failed to submit embed_source for {source_id}: {e}")
                failed_submissions += 1

        # Submit embed_note commands for notes
        logger.info(f"\nSubmitting {len(items['notes'])} note embedding jobs...")
        for idx, note_id in enumerate(items["notes"], 1):
            try:
                submit_command(
                    "open_notebook",
                    "embed_note",
                    {"note_id": note_id},
                )
                notes_submitted += 1

                if idx % 50 == 0 or idx == len(items["notes"]):
                    logger.info(
                        f"  Progress: {idx}/{len(items['notes'])} note jobs submitted"
                    )

            except Exception as e:
                logger.error(f"Failed to submit embed_note for {note_id}: {e}")
                failed_submissions += 1

        # Submit embed_insight commands for insights
        logger.info(f"\nSubmitting {len(items['insights'])} insight embedding jobs...")
        for idx, insight_id in enumerate(items["insights"], 1):
            try:
                submit_command(
                    "open_notebook",
                    "embed_insight",
                    {"insight_id": insight_id},
                )
                insights_submitted += 1

                if idx % 50 == 0 or idx == len(items["insights"]):
                    logger.info(
                        f"  Progress: {idx}/{len(items['insights'])} insight jobs submitted"
                    )

            except Exception as e:
                logger.error(f"Failed to submit embed_insight for {insight_id}: {e}")
                failed_submissions += 1

        processing_time = time.time() - start_time
        jobs_submitted = sources_submitted + notes_submitted + insights_submitted

        logger.info("=" * 60)
        logger.info("REBUILD JOBS SUBMITTED")
        logger.info(f"  Total jobs submitted: {jobs_submitted}/{total_items}")
        logger.info(f"  Sources: {sources_submitted}")
        logger.info(f"  Notes: {notes_submitted}")
        logger.info(f"  Insights: {insights_submitted}")
        logger.info(f"  Failed submissions: {failed_submissions}")
        logger.info(f"  Submission time: {processing_time:.2f}s")
        logger.info("  Note: Actual embedding happens asynchronously")
        logger.info("=" * 60)

        return RebuildEmbeddingsOutput(
            success=True,
            total_items=total_items,
            jobs_submitted=jobs_submitted,
            failed_submissions=failed_submissions,
            sources_submitted=sources_submitted,
            notes_submitted=notes_submitted,
            insights_submitted=insights_submitted,
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Rebuild embeddings failed: {e}")
        logger.exception(e)

        return RebuildEmbeddingsOutput(
            success=False,
            total_items=0,
            jobs_submitted=0,
            failed_submissions=0,
            processing_time=processing_time,
            error_message=str(e),
        )
