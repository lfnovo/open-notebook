from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.notebook import Source


@pytest.mark.asyncio
async def test_source_save_analysis_creates_source_analysis():
    source = Source(id="source:123", title="Video source")

    with patch(
        "open_notebook.domain.source_analysis.SourceAnalysis.save",
        new_callable=AsyncMock,
    ) as mock_save:
        analysis = await source.save_analysis(
            capability="video_understanding",
            provider="openai_compatible",
            model="video-model",
            status="completed",
            normalized_output={"summary": "Done"},
            raw_output={"raw": True},
            rendered_markdown="# Video Understanding",
        )

    mock_save.assert_awaited_once()
    assert analysis.source == "source:123"
    assert analysis.capability == "video_understanding"
