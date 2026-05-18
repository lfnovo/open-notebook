from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.graphs.source import content_process, save_source
from open_notebook.multimodal.types import VideoUnderstandingResult


@pytest.mark.asyncio
@patch("open_notebook.graphs.source.get_video_understanding_provider", new_callable=AsyncMock)
@patch("open_notebook.graphs.source.ModelManager.get_video_understanding_model_config", new_callable=AsyncMock)
@patch("open_notebook.graphs.source.ModelManager.get_defaults", new_callable=AsyncMock)
@patch("open_notebook.graphs.source.extract_content", new_callable=AsyncMock)
async def test_content_process_merges_video_understanding_markdown(
    mock_extract_content,
    mock_get_defaults,
    mock_get_video_model,
    mock_get_provider,
):
    mock_get_defaults.return_value = SimpleNamespace(
        default_speech_to_text_model=None
    )
    mock_extract_content.return_value = SimpleNamespace(
        content="Transcript body",
        url="https://cdn.example.com/video.mp4",
        file_path=None,
        title="Demo",
    )
    mock_get_video_model.return_value = SimpleNamespace(
        id="model:123",
        name="video-model",
        provider="openai_compatible",
        credential=None,
    )
    mock_provider = AsyncMock()
    mock_provider.analyze.return_value = VideoUnderstandingResult(
        summary="Video summary",
        key_events=["Important scene"],
        provider="openai_compatible",
        model="video-model",
    )
    mock_get_provider.return_value = mock_provider

    result = await content_process(
        {
            "content_state": {"url": "https://cdn.example.com/video.mp4"},
            "apply_transformations": [],
            "source_id": "source:1",
            "notebook_ids": [],
            "source": None,
            "transformation": [],
            "embed": False,
            "video_understanding": None,
        }
    )

    assert "Video summary" in result["content_state"].content
    assert result["video_understanding"]["normalized"]["provider"] == "openai_compatible"


@pytest.mark.asyncio
@patch("open_notebook.graphs.source.Source.get", new_callable=AsyncMock)
async def test_save_source_persists_video_analysis(mock_source_get):
    source = SimpleNamespace(
        id="source:1",
        title="Processing...",
        asset=None,
        full_text=None,
        save=AsyncMock(),
        save_analysis=AsyncMock(),
        vectorize=AsyncMock(),
    )
    mock_source_get.return_value = source
    content_state = SimpleNamespace(
        url="https://cdn.example.com/video.mp4",
        file_path=None,
        content="Transcript\n\n# Video Understanding",
        title="Demo title",
    )

    await save_source(
        {
            "content_state": content_state,
            "apply_transformations": [],
            "source_id": "source:1",
            "notebook_ids": [],
            "source": source,
            "transformation": [],
            "embed": False,
            "video_understanding": {
                "normalized": {
                    "provider": "openai_compatible",
                    "model": "video-model",
                },
                "raw_output": {"ok": True},
                "rendered_markdown": "# Video Understanding",
            },
        }
    )

    source.save.assert_awaited_once()
    source.save_analysis.assert_awaited_once()
    assert source.title == "Demo title"
