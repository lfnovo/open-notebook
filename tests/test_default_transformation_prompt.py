"""The Default Transformation Prompt is applied and survives a run (#1465)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage

from open_notebook.domain.transformation import DefaultPrompts
from open_notebook.graphs.transformation import run_transformation

SAVED_PROMPT = "Answer in German."


@pytest.fixture
def saved_default_prompt():
    """A DefaultPrompts singleton loaded from a database row holding SAVED_PROMPT."""
    DefaultPrompts._instances.pop(DefaultPrompts.record_id, None)
    with patch(
        "open_notebook.domain.base.repo_query",
        new=AsyncMock(return_value=[{"transformation_instructions": SAVED_PROMPT}]),
    ):
        yield
    DefaultPrompts._instances.pop(DefaultPrompts.record_id, None)


@pytest.mark.asyncio
async def test_default_prompt_is_prepended_and_not_wiped(saved_default_prompt):
    chain = AsyncMock()
    chain.ainvoke.return_value = AIMessage(
        content="Zusammenfassung", response_metadata={"finish_reason": "stop"}
    )
    transformation = SimpleNamespace(title="Summary", prompt="Summarize this")
    with (
        patch("open_notebook.graphs.transformation.Prompter") as prompter,
        patch(
            "open_notebook.graphs.transformation.provision_langchain_model",
            new=AsyncMock(return_value=chain),
        ),
    ):
        prompter.return_value.render.return_value = "rendered prompt"
        await run_transformation(
            {"transformation": transformation, "input_text": "Source content"},
            {"configurable": {}},
        )

    data = prompter.return_value.render.call_args.kwargs["data"]
    assert data["instructions"] == f"{SAVED_PROMPT}\n\nSummarize this"
    # The editor reads the same singleton: a run must not blank the saved prompt.
    prompts: DefaultPrompts = await DefaultPrompts.get_instance()  # type: ignore[assignment]
    assert prompts.transformation_instructions == SAVED_PROMPT
