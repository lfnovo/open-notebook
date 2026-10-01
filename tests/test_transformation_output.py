"""Incomplete transformations must not become successful insights (#1273)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage
from surreal_commands.core.registry import registry
from surreal_commands.core.retry import build_async_retry_instance

import commands  # noqa: F401 -- register worker retry policies
from open_notebook.domain.notebook import Source
from open_notebook.exceptions import ExternalServiceError, IncompleteGenerationError
from open_notebook.graphs.transformation import run_transformation


@pytest.fixture
def transformation_call():
    source = Source(id="source:test", full_text="Source content")
    transformation = SimpleNamespace(title="Summary", prompt="Summarize this")
    chain = AsyncMock()
    with (
        patch(
            "open_notebook.graphs.transformation.DefaultPrompts",
            return_value=SimpleNamespace(transformation_instructions=None),
        ),
        patch(
            "open_notebook.graphs.transformation.provision_langchain_model",
            new=AsyncMock(return_value=chain),
        ),
        patch.object(Source, "add_insight", new_callable=AsyncMock) as save,
    ):

        async def invoke(content, metadata, with_source=True):
            chain.ainvoke.return_value = AIMessage(
                content=content, response_metadata=metadata
            )
            state: dict = {"transformation": transformation}
            if with_source:
                state["source"] = source
            else:
                state["input_text"] = "Source content"
            return await run_transformation(state, {"configurable": {}})

        yield invoke, save


@pytest.mark.asyncio
@pytest.mark.parametrize("with_source", [True, False])
@pytest.mark.parametrize(
    "metadata",
    [
        {"finish_reason": "length"},
        {"stop_reason": "max_tokens"},
        {"finish_reason": "MAX_TOKENS"},
        {"done_reason": "length"},
    ],
)
async def test_truncated_output_is_rejected(transformation_call, metadata, with_source):
    invoke, save = transformation_call
    with pytest.raises(IncompleteGenerationError, match="generation limit"):
        await invoke("Answer cut mid-wor", metadata, with_source)
    save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("with_source", [True, False])
@pytest.mark.parametrize(
    "content",
    [
        "",
        "   ",
        "<think>Only reasoning</think>",
        "<think>Unfinished reasoning",
    ],
)
async def test_empty_output_is_rejected(transformation_call, content, with_source):
    invoke, save = transformation_call
    with pytest.raises(IncompleteGenerationError, match="no usable text"):
        await invoke(content, {}, with_source)
    save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"finish_reason": "stop"},
        {"stop_reason": "end_turn"},
        {"done_reason": "stop"},
        {"finish_reason": None},
    ],
)
async def test_complete_output_is_saved(transformation_call, metadata):
    invoke, save = transformation_call
    result = await invoke("<think>Reasoning</think>Complete answer.", metadata)
    assert result == {"output": "Complete answer."}
    save.assert_awaited_once_with("Summary", "Complete answer.")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command_id",
    [
        "open_notebook.process_source",
        "open_notebook.run_transformation",
    ],
)
@pytest.mark.parametrize(
    "error, expected_attempts",
    [
        (IncompleteGenerationError("Incomplete output"), 1),
        (ExternalServiceError("Provider unavailable"), 3),
    ],
)
async def test_worker_retry_policy(command_id, error, expected_attempts):
    command = registry.get_command_by_id(command_id)
    config = command.retry_config.model_copy(
        update={
            "max_attempts": 3,
            "wait_strategy": "fixed",
            "wait_time": 0,
            "wait_min": 0,
            "wait_max": 0,
        }
    )
    attempts = 0
    with pytest.raises(type(error)):
        async for attempt in build_async_retry_instance(config):
            with attempt:
                attempts += 1
                raise error
    assert attempts == expected_attempts
