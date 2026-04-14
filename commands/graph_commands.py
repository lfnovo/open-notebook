import time
from typing import Optional

from loguru import logger
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.domain.notebook import Source
from open_notebook.exceptions import ConfigurationError
from open_notebook.services.graph_service import GraphService


class BuildGraphInput(CommandInput):
    """Input for building knowledge graph from a source."""

    workspace_id: str
    source_id: str


class BuildGraphOutput(CommandOutput):
    """Output from graph build command."""

    success: bool
    source_id: str
    processing_time: float
    error_message: Optional[str] = None


@command(
    "build_graph",
    app="open_notebook",
    retry={
        "max_attempts": 3,
        "wait_strategy": "exponential_jitter",
        "wait_min": 2,
        "wait_max": 60,
        "stop_on": [ValueError, ConfigurationError],
        "retry_log_level": "debug",
    },
)
async def build_graph_command(input_data: BuildGraphInput) -> BuildGraphOutput:
    """
    Extract knowledge graph nodes and edges from a source's text content.

    Inserts the source's full_text into the workspace's LightRAG instance.
    On failure, marks source.graph_status as 'warning' so vector search
    continues unaffected.

    Retry Strategy:
    - Retries up to 3 times for transient failures (network, timeout)
    - Does NOT retry validation or configuration errors
    """
    start_time = time.time()

    try:
        logger.info(
            f"Starting graph build for source {input_data.source_id} "
            f"in workspace {input_data.workspace_id}"
        )

        source = await Source.get(input_data.source_id)
        if not source:
            raise ValueError(f"Source '{input_data.source_id}' not found")

        if source.workspace_id and str(source.workspace_id) != str(
            input_data.workspace_id
        ):
            raise ValueError(
                f"Source {input_data.source_id} belongs to workspace {source.workspace_id}, "
                f"not {input_data.workspace_id}"
            )

        if not source.full_text or not source.full_text.strip():
            raise ValueError(
                f"Source '{input_data.source_id}' has no text for graph extraction"
            )

        await GraphService.insert(input_data.workspace_id, source.full_text)

        source.graph_status = "ready"
        await source.save()

        processing_time = time.time() - start_time
        logger.info(
            f"Graph build complete for source {input_data.source_id} "
            f"in {processing_time:.2f}s"
        )

        return BuildGraphOutput(
            success=True,
            source_id=input_data.source_id,
            processing_time=processing_time,
        )

    except ValueError as error:
        processing_time = time.time() - start_time
        logger.error(f"Graph build failed for source {input_data.source_id}: {error}")
        return BuildGraphOutput(
            success=False,
            source_id=input_data.source_id,
            processing_time=processing_time,
            error_message=str(error),
        )

    except Exception as error:
        processing_time = time.time() - start_time
        logger.warning(
            f"Graph extraction failed for source {input_data.source_id}: {error}. "
            "Setting graph_status to 'warning'."
        )

        try:
            source = await Source.get(input_data.source_id)
            if source:
                source.graph_status = "warning"
                await source.save()
        except Exception as save_error:
            logger.error(
                f"Failed to update graph_status for source "
                f"{input_data.source_id}: {save_error}"
            )

        return BuildGraphOutput(
            success=False,
            source_id=input_data.source_id,
            processing_time=processing_time,
            error_message=f"Graph extraction failed: {error}",
        )
