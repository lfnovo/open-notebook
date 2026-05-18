import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.multimodal.providers.openai_compatible_video import (
    OpenAICompatibleVideoProvider,
)
from open_notebook.multimodal.types import VideoUnderstandingInput


@pytest.mark.asyncio
@patch("open_notebook.multimodal.providers.openai_compatible_video.httpx.AsyncClient")
async def test_openai_compatible_video_provider_normalizes_response(mock_client_cls):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "summary": "Video summary",
                                "key_events": ["Event A"],
                                "entities": [
                                    {
                                        "name": "Object A",
                                        "entity_type": "object",
                                        "description": "Detected object",
                                    }
                                ],
                                "timeline": [
                                    {
                                        "start_seconds": 1,
                                        "end_seconds": 5,
                                        "title": "Segment",
                                        "description": "What happens",
                                    }
                                ],
                            }
                        ),
                    }
                ]
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    provider = OpenAICompatibleVideoProvider(
        model_name="video-model",
        base_url="https://example.com/v1",
        api_key="secret",
    )
    result = await provider.analyze(
        VideoUnderstandingInput(
            url="https://cdn.example.com/video.mp4",
            transcript_markdown="Transcript",
        )
    )

    assert result.summary == "Video summary"
    assert result.provider == "openai_compatible"
    assert result.transcript_used is True
    assert result.timeline[0].title == "Segment"
    assert result.entities[0].name == "Object A"


@pytest.mark.asyncio
async def test_openai_compatible_video_provider_requires_url():
    provider = OpenAICompatibleVideoProvider(
        model_name="video-model",
        base_url="https://example.com/v1",
    )

    with pytest.raises(ValueError, match="directly accessible video URL"):
        await provider.analyze(VideoUnderstandingInput(file_path="/tmp/local.mp4"))
