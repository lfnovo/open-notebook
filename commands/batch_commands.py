import time
from typing import List, Optional

from loguru import logger
from surreal_commands import CommandInput, CommandOutput, command

from api.command_service import CommandService
from commands.source_commands import SourceProcessingInput
from open_notebook.database.repository import repo_query
from open_notebook.domain.batch import BatchSourceRelationship, BatchUpload
from open_notebook.domain.notebook import Source


class BatchProcessingInput(CommandInput):
    batch_id: str
    notebook_ids: List[str]
    transformations: List[str]
    embed: bool

class BatchProcessingOutput(CommandOutput):
    success: bool
    batch_id: str
    processed_sources: int
    failed_sources: int
    processing_time: float
    error_message: Optional[str] = None

@command("process_batch_upload", app="open_notebook")
async def process_batch_upload_command(
    input_data: BatchProcessingInput,
) -> BatchProcessingOutput:
    """
    Process a batch of sources.
    """
    start_time = time.time()
    processed_count = 0
    failed_count = 0

    try:
        batch_upload = await BatchUpload.get(input_data.batch_id)
        if not batch_upload:
            raise ValueError(f"BatchUpload '{input_data.batch_id}' not found")

        batch_upload.status = "processing"
        await batch_upload.save()

        # Get all pending sources for this batch
        relationships_data = await repo_query(
            "SELECT * FROM batch_source_relationship WHERE batch_id = $batch_id AND status = 'pending'",
            {"batch_id": input_data.batch_id},
        )
        relationships = [BatchSourceRelationship(**data) for data in relationships_data]

        for rel in relationships:
            try:
                source = await Source.get(rel.source_id)
                if not source:
                    raise ValueError(f"Source '{rel.source_id}' not found")

                # Prepare content_state for processing
                if not source.asset:
                    raise ValueError(f"Source {source.id} has no asset")
                content_state = {"file_path": source.asset.file_path}
                # Submit a processing command for each source
                command_input = SourceProcessingInput(
                    source_id=str(source.id),
                    content_state=content_state,
                    notebook_ids=input_data.notebook_ids,
                    transformations=input_data.transformations,
                    embed=input_data.embed,
                )

                command_id = await CommandService.submit_command_job(
                    "open_notebook",
                    "process_source",
                    command_input.model_dump(),
                )

                # Update source with command reference
                source.command = command_id
                await source.save()

                # Update relationship status
                rel.status = "queued"
                await rel.save()

                processed_count += 1

            except Exception as e:
                logger.error(f"Failed to queue processing for source {rel.source_id} in batch {input_data.batch_id}: {e}")
                rel.status = "failed"
                rel.error_message = str(e)
                await rel.save()
                failed_count += 1

        batch_upload.processed_files = processed_count
        batch_upload.failed_files = failed_count
        if failed_count > 0:
            batch_upload.status = "completed_with_errors"
        else:
            batch_upload.status = "completed"
        await batch_upload.save()

        processing_time = time.time() - start_time
        return BatchProcessingOutput(
            success=True,
            batch_id=input_data.batch_id,
            processed_sources=processed_count,
            failed_sources=failed_count,
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Batch processing failed for batch {input_data.batch_id}: {e}")
        if "batch_upload" in locals() and batch_upload:
            batch_upload.status = "failed"
            await batch_upload.save()
        return BatchProcessingOutput(
            success=False,
            batch_id=input_data.batch_id,
            processed_sources=processed_count,
            failed_sources=failed_count,
            processing_time=processing_time,
            error_message=str(e),
        )
