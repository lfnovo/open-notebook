from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.notebook import graph_search


@pytest.mark.asyncio
@patch("open_notebook.domain.notebook.SearchRepository.graph_subgraphs", new_callable=AsyncMock)
@patch("open_notebook.domain.notebook.SearchRepository.graph_entry_nodes", new_callable=AsyncMock)
async def test_graph_search_handles_entities_without_relationships(
    mock_entry_nodes,
    mock_subgraphs,
):
    mock_entry_nodes.return_value = [
        {
            "id": "kg_entity:bsd",
            "name": "BSD",
            "type": "concept",
            "description": "Berkeley Software Distribution",
            "source_id": "source:bsd",
        }
    ]
    mock_subgraphs.return_value = [
        {
            "id": "kg_entity:bsd",
            "name": "BSD",
            "type": "concept",
            "description": "Berkeley Software Distribution",
            "source_id": "source:bsd",
            "outbound_edges": None,
            "outbound_nodes": None,
            "inbound_edges": None,
            "inbound_nodes": None,
        }
    ]

    results = await graph_search("BSD", results=3)

    assert results == [
        {
            "id": "kg_entity:bsd",
            "source_id": "source:bsd",
            "title": "Knowledge Graph Context for: BSD",
            "content": (
                "Entity: [concept] BSD "
                "(Details: Berkeley Software Distribution)\n"
                "Relationships:\n"
            ),
            "type": "kg_subgraph",
        }
    ]
