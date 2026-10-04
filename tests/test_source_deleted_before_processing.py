"""A source deleted before its process_source job runs must fail permanently.

Regression for the worker-starvation bug: `Source.get()` raises `NotFoundError`
instead of returning `None`, so the `if not source: raise ValueError(...)` guard in
`process_source_command` never fired. `NotFoundError` is not in the command's
`stop_on` list, so the job was retried as a transient failure (up to 15 attempts
with exponential backoff, waits up to 120s) and every job behind it starved —
the worker stopped consuming jobs until the process was restarted.
"""

from unittest.mock import AsyncMock, patch

import pytest

import commands  # noqa: F401 -- import registers the @command decorators
from open_notebook.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_missing_source_raises_permanent_error():
    """NotFoundError from Source.get must surface as ValueError (terminal)."""
    from commands.source_commands import SourceProcessingInput, process_source_command

    input_data = SourceProcessingInput(
        source_id="source:does-not-exist",
        content_state={"file_path": "/tmp/whatever.md"},
        notebook_ids=["notebook:whatever"],
        transformations=[],
        embed=True,
    )

    with patch(
        "commands.source_commands.Source.get",
        new=AsyncMock(
            side_effect=NotFoundError("source with id source:does-not-exist not found")
        ),
    ):
        with pytest.raises(ValueError) as excinfo:
            await process_source_command(input_data)

    assert "no longer exists" in str(excinfo.value)
    # The retry policy keys off the exception type: ValueError is in `stop_on`,
    # NotFoundError is not — that difference is the whole fix.
    assert not isinstance(excinfo.value, NotFoundError)


@pytest.mark.asyncio
async def test_missing_transformation_raises_permanent_error():
    """A transformation deleted before the job runs is just as permanent."""
    from commands.source_commands import SourceProcessingInput, process_source_command

    input_data = SourceProcessingInput(
        source_id="source:abc",
        content_state={"file_path": "/tmp/whatever.md"},
        notebook_ids=["notebook:whatever"],
        transformations=["transformation:gone"],
        embed=True,
    )

    with patch(
        "commands.source_commands.Transformation.get",
        new=AsyncMock(side_effect=NotFoundError("transformation not found")),
    ):
        with pytest.raises(ValueError, match="no longer exists"):
            await process_source_command(input_data)


@pytest.mark.asyncio
async def test_object_get_reports_db_failures_as_database_errors():
    """ObjectModel.get used to wrap every exception (e.g. a retriable SurrealDB
    transaction conflict) as NotFoundError, so the fix above would have made
    transient failures permanent. Only a missing record is NotFoundError."""
    from open_notebook.domain.notebook import Source
    from open_notebook.exceptions import DatabaseOperationError

    with patch(
        "open_notebook.domain.base.repo_query",
        new=AsyncMock(side_effect=RuntimeError("Transaction conflict: retry")),
    ):
        with pytest.raises(DatabaseOperationError):
            await Source.get("source:abc")

    with patch("open_notebook.domain.base.repo_query", new=AsyncMock(return_value=[])):
        with pytest.raises(NotFoundError):
            await Source.get("source:abc")


@pytest.mark.asyncio
async def test_transient_db_failure_stays_retryable():
    """A database failure while loading the source is re-raised as is (not
    ValueError), so the worker's retry policy still applies."""
    from commands.source_commands import SourceProcessingInput, process_source_command
    from open_notebook.exceptions import DatabaseOperationError

    input_data = SourceProcessingInput(
        source_id="source:abc",
        content_state={"file_path": "/tmp/whatever.md"},
        notebook_ids=["notebook:whatever"],
        transformations=[],
        embed=True,
    )

    with patch(
        "commands.source_commands.Source.get",
        new=AsyncMock(side_effect=DatabaseOperationError("Failed to fetch")),
    ):
        with pytest.raises(DatabaseOperationError):
            await process_source_command(input_data)


@pytest.mark.asyncio
async def test_run_transformation_fails_permanently_when_source_is_gone():
    """run_transformation had the same deletion-before-processing gap."""
    from surreal_commands import registry

    from commands.source_commands import (
        RunTransformationInput,
        run_transformation_command,
    )

    with patch(
        "commands.source_commands.Source.get",
        new=AsyncMock(side_effect=NotFoundError("source not found")),
    ):
        with pytest.raises(NotFoundError):
            await run_transformation_command(
                RunTransformationInput(
                    source_id="source:gone", transformation_id="transformation:t1"
                )
            )

    command = registry.get_command("open_notebook", "run_transformation")
    assert command is not None
    assert NotFoundError in command.retry_config.stop_on


@pytest.mark.asyncio
async def test_source_deleted_during_processing_fails_permanently():
    """save_source re-reads the source after extraction; a deletion in that
    window raises NotFoundError from inside the graph, which must not be
    retried either."""
    from types import SimpleNamespace

    from surreal_commands import registry

    from commands.source_commands import SourceProcessingInput, process_source_command

    source = SimpleNamespace(id="source:abc", command=None, save=AsyncMock())
    with (
        patch(
            "commands.source_commands.Source.get", new=AsyncMock(return_value=source)
        ),
        patch(
            "commands.source_commands.source_graph.ainvoke",
            new=AsyncMock(
                side_effect=NotFoundError("source with id source:abc not found")
            ),
        ),
    ):
        with pytest.raises(NotFoundError):
            await process_source_command(
                SourceProcessingInput(
                    source_id="source:abc",
                    content_state={"file_path": "/tmp/x.md"},
                    notebook_ids=[],
                    transformations=[],
                    embed=False,
                )
            )

    command = registry.get_command("open_notebook", "process_source")
    assert command is not None
    assert NotFoundError in command.retry_config.stop_on
