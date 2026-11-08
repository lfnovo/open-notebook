"""A NUL byte in source text must not leave a `command` row behind (#1558).

SurrealDB stores a record holding a NUL byte but then fails to serialize it.
`submit_command()` writes the row before the error comes back and never
returns its id, and the worker's queue query then fails on every poll. So NUL
bytes are rejected before the source is saved or a command is submitted.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.command_service import CommandService
from api.models import SourceCreate, SourceUpdate
from open_notebook.domain.notebook import Source
from open_notebook.exceptions import InvalidInputError

NUL_TEXT = "page one\x00page two"


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.fixture
def db_writes():
    """Stand-ins for every write the create path makes; on code without the
    check the request reaches them and the tests fail on the assertions."""
    submit = MagicMock(return_value="command:abc")
    with (
        patch("api.command_service.submit_command", submit),
        patch.object(Source, "save", AsyncMock()) as save,
        patch.object(Source, "add_to_notebook", AsyncMock()),
    ):
        yield {"submit_command": submit, "source_save": save}


@pytest.mark.parametrize("field", ["content", "title", "url"])
def test_source_create_rejects_nul_byte(field):
    data = {"type": "text", "content": "hi", field: NUL_TEXT}

    with pytest.raises(ValidationError, match="NUL byte"):
        SourceCreate(**data)


def test_source_create_accepts_text_without_nul_byte():
    assert SourceCreate(type="text", content="page one\npage two").content


@pytest.mark.parametrize("data", [{"title": NUL_TEXT}, {"topics": ["ok", NUL_TEXT]}])
def test_source_update_rejects_nul_byte(data):
    with pytest.raises(ValidationError, match="NUL byte"):
        SourceUpdate(**data)


def test_source_update_with_nul_byte_is_not_saved(client):
    with (
        patch(
            "api.routers.sources.Source.get", AsyncMock(return_value=Source(title="a"))
        ),
        patch.object(Source, "save", AsyncMock()) as save,
        patch.object(Source, "get_embedded_chunks", AsyncMock(return_value=0)),
    ):
        response = client.put("/api/sources/source:abc", json={"title": NUL_TEXT})

    assert response.status_code == 422
    assert "NUL byte" in response.text
    save.assert_not_awaited()


@pytest.mark.parametrize("async_processing", [True, False])
def test_json_request_with_nul_byte_leaves_no_command_row(
    client, db_writes, async_processing
):
    response = client.post(
        "/api/sources/json",
        json={
            "type": "text",
            "content": NUL_TEXT,
            "async_processing": async_processing,
        },
    )

    assert response.status_code == 422
    assert "NUL byte" in response.text
    db_writes["submit_command"].assert_not_called()
    db_writes["source_save"].assert_not_awaited()


def test_form_request_with_nul_byte_leaves_no_command_row(client, db_writes):
    response = client.post(
        "/api/sources",
        data={"type": "text", "content": NUL_TEXT, "async_processing": "true"},
    )

    assert response.status_code == 422
    assert "NUL byte" in response.json()["detail"]
    db_writes["submit_command"].assert_not_called()
    db_writes["source_save"].assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [
        {"source_id": "source:x", "content_state": {"content": NUL_TEXT}},
        {"source_id": "source:x", "content_state": {NUL_TEXT: "clean"}},
        {"source_id": "source:x", "transformations": ["ok", NUL_TEXT]},
    ],
    ids=["nested-value", "dict-key", "list-item"],
)
async def test_submit_command_job_refuses_nul_byte(args):
    submit = MagicMock(return_value="command:abc")

    with (
        patch("api.command_service.submit_command", submit),
        pytest.raises(InvalidInputError, match="NUL byte"),
    ):
        await CommandService.submit_command_job("open_notebook", "process_source", args)

    submit.assert_not_called()


@pytest.mark.asyncio
async def test_submit_command_job_submits_clean_args():
    submit = MagicMock(return_value="command:abc")
    args = {"source_id": "source:x", "content_state": {"content": ["a", "b"]}}

    with patch("api.command_service.submit_command", submit):
        command_id = await CommandService.submit_command_job(
            "open_notebook", "process_source", args
        )

    assert command_id == "command:abc"
    submit.assert_called_once_with("open_notebook", "process_source", args)


def test_async_embed_with_nul_byte_returns_400_and_submits_nothing(client):
    # Other callers of submit_command_job get the same guard; the typed error
    # must reach the global handler, not the router's catch-all 500.
    submit = MagicMock(return_value="command:abc")

    with (
        patch("api.command_service.submit_command", submit),
        patch(
            "open_notebook.ai.models.model_manager.get_embedding_model",
            new=AsyncMock(return_value=object()),
        ),
    ):
        response = client.post(
            "/api/embed",
            json={
                "item_id": f"source:{NUL_TEXT}",
                "item_type": "source",
                "async_processing": True,
            },
        )

    assert response.status_code == 400
    assert "NUL byte" in response.json()["detail"]
    submit.assert_not_called()
