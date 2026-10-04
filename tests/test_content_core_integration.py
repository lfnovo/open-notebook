"""Open Notebook's integration with content-core >= 2.1 (#1408).

- content-core disables its own Loguru logging for library consumers; we
  re-enable it so extraction logs reach the API and worker output.
- An explicit document_engine="docling" raises ConfigurationError in
  content-core when the runtime is missing; _usable_engine() must downgrade a
  stored Docling selection to "auto" before it reaches content-core.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from loguru import logger


def test_content_core_logs_are_enabled():
    import open_notebook.graphs.source  # noqa: F401  (enables content_core logs)

    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(m.record["message"]), level="INFO")
    try:
        # Log as if from inside content-core: Loguru filters on the caller's
        # module name.
        exec(
            "logger.info('from content-core')",
            {"logger": logger, "__name__": "content_core.extraction"},
        )
    finally:
        logger.remove(sink_id)

    assert "from content-core" in messages


@pytest.mark.asyncio
async def test_docling_selection_falls_back_to_auto_when_runtime_missing():
    from open_notebook.graphs import source as source_graph

    settings = SimpleNamespace(
        youtube_preferred_languages=None,
        default_content_processing_engine_url=None,
        default_content_processing_engine_doc="docling",
        docling_ocr=None,
        docling_formulas=None,
        docling_vision=None,
    )
    extracted = SimpleNamespace(title="Doc", content="some text")

    with (
        patch.object(
            source_graph.ContentSettings,
            "get_instance",
            new=AsyncMock(return_value=settings),
        ),
        patch.object(
            source_graph,
            "engine_runtime_missing",
            side_effect=lambda e: "OPEN_NOTEBOOK_ENABLE_DOCLING"
            if e == "docling"
            else None,
        ),
        patch.object(
            source_graph.ModelManager,
            "get_defaults",
            new=AsyncMock(
                return_value=SimpleNamespace(default_speech_to_text_model=None)
            ),
        ),
        patch.object(
            source_graph, "extract_content", new=AsyncMock(return_value=extracted)
        ) as mock_extract,
    ):
        await source_graph.content_process(
            {"content_state": {"file_path": "/tmp/doc.pdf"}}  # type: ignore[typeddict-item]
        )

    config = mock_extract.call_args.kwargs["config"]
    assert config.document_engine == "auto"
