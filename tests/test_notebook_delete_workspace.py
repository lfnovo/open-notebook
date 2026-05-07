from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.notebook import Notebook, Source


@pytest.mark.asyncio
async def test_notebook_delete_does_not_delete_exclusive_external_sources():
    notebook = Notebook(
        id="notebook:team",
        name="Team notebook",
        description="",
        owner_id="app_user:owner",
        workspace_id="workspace:team",
    )
    external_source = Source(
        id="source:external",
        title="External source",
        owner_id="app_user:other",
        workspace_id="workspace:personal",
        visibility="private",
    )
    captured = {}

    async def capture_delete_transaction(
        notebook_id,
        *,
        exclusive_source_ids,
        include_knowledge_graph,
    ):
        captured["notebook_id"] = notebook_id
        captured["exclusive_source_ids"] = exclusive_source_ids
        captured["include_knowledge_graph"] = include_knowledge_graph

    with patch(
        "open_notebook.domain.notebook.NotebookRepository.note_count",
        new_callable=AsyncMock,
        return_value=0,
    ), patch(
        "open_notebook.domain.notebook.NotebookRepository.source_reference_counts",
        new_callable=AsyncMock,
        return_value=[{"id": "source:external", "assigned_others": 0}],
    ), patch.object(
        Source,
        "get",
        new_callable=AsyncMock,
        return_value=external_source,
    ), patch(
        "open_notebook.domain.notebook.NotebookRepository.delete_notebook_records_transaction",
        new_callable=AsyncMock,
        side_effect=capture_delete_transaction,
    ):
        result = await notebook.delete(delete_exclusive_sources=True)

    assert captured["notebook_id"] == "notebook:team"
    assert captured["exclusive_source_ids"] == []
    assert result["deleted_sources"] == 0
    assert result["unlinked_sources"] == 1
