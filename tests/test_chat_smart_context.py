"""Tests for smart-chat context classification and scoped vector_search wiring."""

from unittest.mock import AsyncMock, patch

import pytest

from api.routers.chat import _classify_source_modes


def test_classify_source_modes_splits_full_auto_off():
    cfg = {
        "sources": {
            "source:a": "full content",
            "source:b": "auto",
            "source:c": "insights",  # legacy -> retrieval pool
            "source:d": "not in context",
            "e": "auto",  # id without prefix gets normalized
        },
        "notes": {
            "note:n1": "full content",
            "note:n2": "not in",
        },
    }
    full, auto, note_full = _classify_source_modes(cfg)
    assert full == ["source:a"]
    assert set(auto) == {"source:b", "source:c", "source:e"}
    assert note_full == ["note:n1"]


def test_classify_source_modes_empty():
    assert _classify_source_modes({}) == ([], [], [])


@pytest.mark.asyncio
async def test_vector_search_passes_source_ids_to_db():
    with patch(
        "open_notebook.utils.embedding.generate_embedding",
        new=AsyncMock(return_value=[0.1, 0.2, 0.3]),
    ), patch(
        "open_notebook.domain.notebook.repo_query", new=AsyncMock(return_value=[])
    ) as mock_query:
        from open_notebook.domain.notebook import vector_search

        await vector_search("pricing", 5, source_ids=["source:a", "source:b"])

    # The scoped source ids must reach the SurrealDB function call.
    _, kwargs = mock_query.call_args
    params = kwargs.get("vars") or mock_query.call_args.args[1]
    assert params["source_ids"] == ["source:a", "source:b"]
    assert "$source_ids" in mock_query.call_args.args[0]


@pytest.mark.asyncio
async def test_vector_search_defaults_source_ids_empty():
    with patch(
        "open_notebook.utils.embedding.generate_embedding",
        new=AsyncMock(return_value=[0.1, 0.2, 0.3]),
    ), patch(
        "open_notebook.domain.notebook.repo_query", new=AsyncMock(return_value=[])
    ) as mock_query:
        from open_notebook.domain.notebook import vector_search

        await vector_search("pricing", 5)

    params = mock_query.call_args.args[1]
    assert params["source_ids"] == []
