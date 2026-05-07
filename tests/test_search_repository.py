from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.database.repositories.search_repository import SearchRepository


@pytest.mark.asyncio
@patch("open_notebook.database.repositories.search_repository.repo_query", new_callable=AsyncMock)
async def test_vector_search_preserves_chunk_matches(mock_repo_query):
    mock_repo_query.side_effect = [
        [
            {
                "id": "source:item",
                "parent_id": "source:item",
                "title": "Source item",
                "content": "First matched chunk",
                "similarity": 0.9,
            },
            {
                "id": "source:item",
                "parent_id": "source:item",
                "title": "Source item",
                "content": "Second matched chunk",
                "similarity": 0.7,
            },
        ],
        [],
        [
            {
                "id": "note:item",
                "parent_id": "note:item",
                "title": "Note item",
                "content": "Matched note content",
                "similarity": 0.8,
            }
        ],
    ]

    results = await SearchRepository.vector_search(
        [0.1, 0.2],
        10,
        source=True,
        note=True,
        minimum_score=0.2,
    )

    assert results == [
        {
            "id": "source:item",
            "parent_id": "source:item",
            "title": "Source item",
            "similarity": 0.9,
            "matches": ["First matched chunk", "Second matched chunk"],
        },
        {
            "id": "note:item",
            "parent_id": "note:item",
            "title": "Note item",
            "similarity": 0.8,
            "matches": ["Matched note content"],
        },
    ]

