"""POST /sources/{id}/insights refuses sources with no text, so the
transformation job is never queued (#1394)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.mark.parametrize("full_text", [None, "", "  \n "])
def test_source_without_text_returns_400_and_queues_nothing(client, full_text):
    with (
        patch(
            "api.routers.sources.Source.get",
            new=AsyncMock(return_value=SimpleNamespace(full_text=full_text)),
        ),
        patch("api.routers.sources.Transformation.get", new=AsyncMock()),
        patch("api.routers.sources.submit_command", new=MagicMock()) as mock_submit,
    ):
        response = client.post(
            "/api/sources/source:abc/insights",
            json={"transformation_id": "transformation:t1"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Source has no text content"
    mock_submit.assert_not_called()


def test_source_with_text_is_queued(client):
    with (
        patch(
            "api.routers.sources.Source.get",
            new=AsyncMock(return_value=SimpleNamespace(full_text="some text")),
        ),
        patch("api.routers.sources.Transformation.get", new=AsyncMock()),
        patch(
            "api.routers.sources.submit_command",
            new=MagicMock(return_value="command:1"),
        ) as mock_submit,
    ):
        response = client.post(
            "/api/sources/source:abc/insights",
            json={"transformation_id": "transformation:t1"},
        )

    assert response.status_code == 202
    mock_submit.assert_called_once_with(
        "open_notebook",
        "run_transformation",
        {"source_id": "source:abc", "transformation_id": "transformation:t1"},
    )


@pytest.mark.asyncio
async def test_worker_treats_invalid_input_as_permanent():
    """An InvalidInputError from the graph (e.g. its empty-content guard) ends
    the job as failed: re-raised, and in stop_on so it is not retried. The
    guard itself is covered in tests/test_graphs.py."""
    from commands.source_commands import (
        RunTransformationInput,
        run_transformation_command,
    )
    from open_notebook.exceptions import InvalidInputError

    with (
        patch(
            "commands.source_commands.Source.get",
            new=AsyncMock(return_value=SimpleNamespace(full_text="")),
        ),
        patch(
            "commands.source_commands.Transformation.get",
            new=AsyncMock(return_value=SimpleNamespace(model_id=None)),
        ),
        patch(
            "commands.source_commands.transform_graph.ainvoke",
            new=AsyncMock(
                side_effect=InvalidInputError("There is no text content to transform")
            ),
        ),
    ):
        with pytest.raises(InvalidInputError):
            await run_transformation_command(
                RunTransformationInput(
                    source_id="source:abc", transformation_id="transformation:t1"
                )
            )


@pytest.mark.asyncio
async def test_source_processing_skips_transformations_on_whitespace_text():
    """process_source applies default transformations through the source graph;
    whitespace-only text is skipped there instead of failing the job."""
    from open_notebook.graphs.source import transform_content

    source = SimpleNamespace(full_text="  \n ", add_insight=AsyncMock())
    with patch(
        "open_notebook.graphs.source.transform_graph.ainvoke", new=AsyncMock()
    ) as mock_invoke:
        result = await transform_content(
            {"source": source, "transformation": SimpleNamespace(name="t")}  # type: ignore[typeddict-item]
        )

    assert result is None
    mock_invoke.assert_not_called()
    source.add_insight.assert_not_called()
