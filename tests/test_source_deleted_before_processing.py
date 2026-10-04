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
