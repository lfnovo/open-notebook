from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.ai.connection_tester import (
    test_individual_model as run_individual_model_test,
)


@pytest.mark.asyncio
@patch("open_notebook.multimodal.registry.get_video_understanding_provider", new_callable=AsyncMock)
async def test_test_individual_model_uses_real_video_provider_connection(
    mock_get_provider,
):
    provider = AsyncMock()
    provider.test_connection.return_value = (True, "Connected. 1 models available.")
    mock_get_provider.return_value = provider

    model = type(
        "ModelStub",
        (),
        {"type": "video_understanding", "id": "model:1", "provider": "openai_compatible"},
    )()

    success, message = await run_individual_model_test(model)

    assert success is True
    assert "Connected." in message
    provider.test_connection.assert_awaited_once()
