from unittest.mock import AsyncMock

import pytest
from surreal_commands import registry

import commands
import commands.embedding_commands as embedding_commands


def test_legacy_embedding_commands_are_registered():
    app_commands = registry.list_commands()["open_notebook"]

    assert "embed_chunk" in app_commands
    assert "embed_single_item" in app_commands
    assert "vectorize_source" in app_commands


@pytest.mark.asyncio
async def test_legacy_embed_chunk_processes_stale_queue_payload(monkeypatch):
    mock_generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
    mock_repo_query = AsyncMock()

    monkeypatch.setattr(
        embedding_commands, "generate_embedding", mock_generate_embedding
    )
    monkeypatch.setattr(embedding_commands, "repo_query", mock_repo_query)
    monkeypatch.setattr(
        embedding_commands, "ensure_record_id", lambda value: f"record:{value}"
    )

    result = await embedding_commands.legacy_embed_chunk_command(
        embedding_commands.LegacyEmbedChunkInput(
            source_id="source:abc",
            chunk_index=2,
            chunk_text="queued legacy chunk",
        )
    )

    assert result.success is True
    assert result.source_id == "source:abc"
    assert result.chunk_index == 2
    mock_generate_embedding.assert_awaited_once_with(
        "queued legacy chunk",
        content_type=embedding_commands.ContentType.PLAIN,
        command_id="unknown",
    )
    mock_repo_query.assert_awaited_once()
    assert mock_repo_query.await_args is not None
    assert mock_repo_query.await_args.args[1] == {
        "source_id": "record:source:abc",
        "order": 2,
        "content": "queued legacy chunk",
        "embedding": [0.1, 0.2, 0.3],
    }


@pytest.mark.asyncio
async def test_legacy_vectorize_source_delegates_to_embed_source(monkeypatch):
    async def fake_embed_source(input_data):
        assert input_data.source_id == "source:abc"
        return embedding_commands.EmbedSourceOutput(
            success=True,
            source_id=input_data.source_id,
            chunks_created=3,
            processing_time=0.1,
        )

    monkeypatch.setattr(embedding_commands, "embed_source_command", fake_embed_source)

    result = await embedding_commands.legacy_vectorize_source_command(
        embedding_commands.LegacyVectorizeSourceInput(source_id="source:abc")
    )

    assert result.success is True
    assert result.source_id == "source:abc"
    assert result.total_chunks == 3
    assert result.jobs_submitted == 1


@pytest.mark.asyncio
async def test_legacy_embed_single_item_routes_insights(monkeypatch):
    async def fake_embed_insight(input_data):
        assert input_data.insight_id == "source_insight:abc"
        return embedding_commands.EmbedInsightOutput(
            success=True,
            insight_id=input_data.insight_id,
            processing_time=0.1,
        )

    monkeypatch.setattr(embedding_commands, "embed_insight_command", fake_embed_insight)

    result = await embedding_commands.legacy_embed_single_item_command(
        embedding_commands.LegacyEmbedSingleItemInput(
            item_id="source_insight:abc",
            item_type="insight",
        )
    )

    assert result.success is True
    assert result.item_id == "source_insight:abc"
    assert result.item_type == "insight"
    assert result.chunks_created == 0
