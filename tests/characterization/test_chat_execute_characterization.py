"""Characterization: chat over a notebook.

Captures the CURRENT behavior of POST /api/chat/execute as of `upstream-base`.
See ./README.md before changing anything here.

`/chat/execute` is the path that turns a user message plus a notebook's context
into an AI reply. The LangGraph chat graph is mocked — these tests characterize
the router's contract (session lookup, notebook resolution, model-override
precedence, state assembly, response shape), not the LLM.

Session CRUD and message shapes are already covered by
`tests/test_chat_routers_characterization.py`; this file deliberately does not
repeat them.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _message(msg_id, msg_type, content):
    """A stand-in for a LangChain message (duck-typed by extract_chat_messages)."""
    return SimpleNamespace(id=msg_id, type=msg_type, content=content)


@pytest.fixture
def chat_env():
    """Patch the whole chat-execution surface: session lookup, notebook lookup,
    and the LangGraph chat graph.

    Yields a namespace of the mocks so each test can assert on them.
    """
    session = MagicMock()
    session.model_override = None
    session.save = AsyncMock()

    with (
        patch(
            "api.routers.chat.get_session_or_404", new_callable=AsyncMock
        ) as mock_session,
        patch("api.routers.chat.repo_query", new_callable=AsyncMock) as mock_query,
        patch("api.routers.chat.Notebook.get", new_callable=AsyncMock) as mock_nb,
        patch("api.routers.chat.chat_graph") as mock_graph,
    ):
        mock_session.return_value = ("chat_session:abc", session)
        mock_query.return_value = [{"out": "notebook:1"}]
        mock_nb.return_value = MagicMock()
        mock_graph.get_state.return_value = SimpleNamespace(values={})
        mock_graph.invoke.return_value = {
            "messages": [
                _message("m1", "human", "Hello"),
                _message("m2", "ai", "Hi, how can I help?"),
            ]
        }

        yield SimpleNamespace(
            session=session,
            get_session=mock_session,
            repo_query=mock_query,
            notebook_get=mock_nb,
            graph=mock_graph,
        )


class TestHappyPath:
    def test_execute_returns_the_full_message_list(self, client, chat_env):
        response = client.post(
            "/api/chat/execute",
            json={
                "session_id": "chat_session:abc",
                "message": "Hello",
                "context": {"sources": [], "notes": []},
            },
        )

        assert response.status_code == 200
        body = response.json()
        # The response echoes back the session_id AS SENT, not the normalized one.
        assert body["session_id"] == "chat_session:abc"
        # The whole conversation is returned, not just the new reply.
        assert [m["type"] for m in body["messages"]] == ["human", "ai"]
        assert body["messages"][1]["content"] == "Hi, how can I help?"
        # LangChain messages carry no timestamp.
        assert body["messages"][0]["timestamp"] is None

    def test_bare_session_id_is_normalized_before_lookup(self, client, chat_env):
        """A session id without its table prefix is prefixed by the router."""
        client.post(
            "/api/chat/execute",
            json={"session_id": "abc", "message": "Hello", "context": {}},
        )

        chat_env.get_session.assert_awaited_once_with("abc")

    def test_user_message_is_appended_to_graph_state(self, client, chat_env):
        client.post(
            "/api/chat/execute",
            json={
                "session_id": "chat_session:abc",
                "message": "What does the report say?",
                "context": {"sources": ["source:1"]},
            },
        )

        state = chat_env.graph.invoke.call_args.kwargs["input"]
        assert state["messages"][-1].content == "What does the report say?"
        assert state["messages"][-1].type == "human"
        # The request's context is placed on the state verbatim.
        assert state["context"] == {"sources": ["source:1"]}
        # The resolved notebook is attached so the graph can use its content.
        assert state["notebook"] is chat_env.notebook_get.return_value

    def test_thread_id_is_the_normalized_session_id(self, client, chat_env):
        client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "Hi", "context": {}},
        )

        config = chat_env.graph.invoke.call_args.kwargs["config"]
        assert config["configurable"]["thread_id"] == "chat_session:abc"

    def test_session_is_saved_to_bump_its_timestamp(self, client, chat_env):
        client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "Hi", "context": {}},
        )

        chat_env.session.save.assert_awaited_once()

    def test_existing_conversation_state_is_carried_forward(self, client, chat_env):
        """Prior messages from the checkpoint are preserved and the new message
        is appended after them."""
        chat_env.graph.get_state.return_value = SimpleNamespace(
            values={"messages": [_message("m0", "ai", "Earlier reply")]}
        )

        client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "Follow up", "context": {}},
        )

        state = chat_env.graph.invoke.call_args.kwargs["input"]
        assert len(state["messages"]) == 2
        assert state["messages"][0].content == "Earlier reply"
        assert state["messages"][1].content == "Follow up"


class TestNotebookResolution:
    def test_notebook_is_resolved_via_the_refers_to_edge(self, client, chat_env):
        client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "Hi", "context": {}},
        )

        chat_env.notebook_get.assert_awaited_once_with("notebook:1")

    def test_session_with_no_notebook_still_executes(self, client, chat_env):
        """A session not linked to any notebook chats with notebook=None rather
        than erroring."""
        chat_env.repo_query.return_value = []

        response = client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "Hi", "context": {}},
        )

        assert response.status_code == 200
        chat_env.notebook_get.assert_not_awaited()
        assert chat_env.graph.invoke.call_args.kwargs["input"]["notebook"] is None


class TestModelOverridePrecedence:
    def test_request_override_wins_over_session_override(self, client, chat_env):
        chat_env.session.model_override = "model:session"

        client.post(
            "/api/chat/execute",
            json={
                "session_id": "chat_session:abc",
                "message": "Hi",
                "context": {},
                "model_override": "model:request",
            },
        )

        config = chat_env.graph.invoke.call_args.kwargs["config"]
        assert config["configurable"]["model_id"] == "model:request"

    def test_session_override_used_when_request_omits_one(self, client, chat_env):
        chat_env.session.model_override = "model:session"

        client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "Hi", "context": {}},
        )

        config = chat_env.graph.invoke.call_args.kwargs["config"]
        assert config["configurable"]["model_id"] == "model:session"

    def test_no_override_anywhere_passes_none(self, client, chat_env):
        chat_env.session.model_override = None

        client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "Hi", "context": {}},
        )

        config = chat_env.graph.invoke.call_args.kwargs["config"]
        assert config["configurable"]["model_id"] is None


class TestErrorHandling:
    def test_missing_session_returns_404(self, client):
        from fastapi import HTTPException

        with patch(
            "api.routers.chat.get_session_or_404", new_callable=AsyncMock
        ) as mock_session:
            mock_session.side_effect = HTTPException(
                status_code=404, detail="Session not found"
            )
            response = client.post(
                "/api/chat/execute",
                json={"session_id": "chat_session:ghost", "message": "Hi", "context": {}},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"

    def test_graph_failure_returns_500(self, client, chat_env):
        chat_env.graph.invoke.side_effect = RuntimeError("model provider is down")

        response = client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "Hi", "context": {}},
        )

        assert response.status_code == 500
        # NOTE: the raw provider error text reaches the client here.
        assert "Error executing chat" in response.json()["detail"]

    @pytest.mark.parametrize(
        "payload",
        [
            {"message": "Hi", "context": {}},  # no session_id
            {"session_id": "chat_session:abc", "context": {}},  # no message
            {"session_id": "chat_session:abc", "message": "Hi"},  # no context
        ],
    )
    def test_missing_required_fields_return_422(self, payload, client):
        """`context` is required — there is no default empty context."""
        response = client.post("/api/chat/execute", json=payload)
        assert response.status_code == 422
