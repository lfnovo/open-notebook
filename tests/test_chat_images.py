"""Multimodal ingestion, graph payloads and checkpoint round trips."""

import base64
from io import BytesIO
from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from PIL import Image
from pydantic import ValidationError

from api.routers._chat_shared import extract_chat_messages
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.chat_images import (
    MAX_CHAT_IMAGE_BYTES,
    ChatImage,
    ChatInput,
    build_user_message,
    chat_model_context,
)
from open_notebook.utils.error_classifier import classify_error


def _image(format="PNG", mime="image/png"):
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "red").save(buffer, format=format)
    return {
        "name": "diagram.png",
        "data_url": f"data:{mime};base64,"
        + base64.b64encode(buffer.getvalue()).decode(),
    }


@pytest.mark.parametrize(
    "format,mime",
    [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")],
)
def test_supported_image_formats(format, mime):
    image = ChatImage(**_image(format, mime))
    assert image.data_url.startswith(f"data:{mime};base64,")


@pytest.mark.parametrize(
    "data_url",
    [
        "https://example.com/image.png",
        "file:///etc/passwd",
        "data:image/svg+xml;base64,PHN2Zz4=",
        "data:image/png;base64,@@@",
        "data:image/png;base64,",
        "data:image/png;base64,aGVsbG8=",
    ],
)
def test_rejects_remote_urls_and_invalid_images(data_url):
    with pytest.raises(ValidationError):
        ChatImage(name="image", data_url=data_url)


def test_mime_must_match_actual_image():
    image = _image()
    image["data_url"] = image["data_url"].replace("image/png", "image/jpeg")
    with pytest.raises(ValidationError, match="declared format"):
        ChatImage(**image)


def test_rejects_oversized_image_and_excessive_dimensions():
    encoded = base64.b64encode(b"x" * (MAX_CHAT_IMAGE_BYTES + 1)).decode()
    with pytest.raises(ValidationError):
        ChatImage(name="large.png", data_url="data:image/png;base64," + encoded)
    buffer = BytesIO()
    Image.new("1", (5001, 5000)).save(buffer, format="PNG")
    with pytest.raises(ValidationError, match="25 megapixels"):
        ChatImage(
            name="large.png",
            data_url="data:image/png;base64,"
            + base64.b64encode(buffer.getvalue()).decode(),
        )


def test_request_allows_image_only_and_requires_some_content():
    assert ChatInput(images=[_image()]).message == ""
    assert ChatInput(message="hello").images == []
    with pytest.raises(ValidationError, match="required"):
        ChatInput(message=" \n")
    with pytest.raises(ValidationError):
        ChatInput(images=[_image()] * 5)


def test_multimodal_text_and_filenames_survive_sqlite_checkpoint(tmp_path):
    from open_notebook.graphs.chat import ThreadState

    image = ChatImage(**{**_image(), "name": "../diagram.png"})
    user = build_user_message("Explain this diagram", [image])
    workflow = StateGraph(ThreadState)
    workflow.add_node(
        "reply", lambda state: {"messages": [AIMessage(content="A red diagram")]}
    )
    workflow.add_edge(START, "reply")
    workflow.add_edge("reply", END)
    config = RunnableConfig(configurable={"thread_id": "chat_session:images"})
    with SqliteSaver.from_conn_string(str(tmp_path / "checkpoints.sqlite")) as saver:
        graph = workflow.compile(checkpointer=saver)
        graph.invoke(
            cast(
                Any,
                ThreadState(
                    messages=[user],
                    notebook=None,
                    context=None,
                    context_config=None,
                    model_override=None,
                ),
            ),
            config,
        )
    # Open the file again as a subsequent API process would.
    with SqliteSaver.from_conn_string(str(tmp_path / "checkpoints.sqlite")) as saver:
        restored = workflow.compile(checkpointer=saver).get_state(config)
    messages = extract_chat_messages(restored.values["messages"])
    assert messages[0].content == "Explain this diagram"
    assert messages[0].images == [image]
    assert messages[0].images[0].name == "diagram.png"
    assert messages[1].content == "A red diagram"
    assert messages[1].images == []


@pytest.mark.parametrize("source_chat", [False, True])
def test_both_graphs_deliver_images_to_model_without_counting_base64(source_chat):
    from open_notebook.graphs import chat
    from open_notebook.graphs import source_chat as source

    module = source if source_chat else chat
    node: Callable[..., dict] = (
        source.call_model_with_source_context
        if source_chat
        else chat.call_model_with_messages
    )
    image = ChatImage(**_image())
    user = build_user_message("What is shown?", [image])
    model = MagicMock()
    model.invoke.return_value = AIMessage(content="A red image")
    provision = AsyncMock(return_value=model)
    with (
        patch.object(module, "provision_langchain_model", new=provision),
        patch.object(module, "Prompter") as prompter,
        patch.object(
            source,
            "build_source_context",
            new=AsyncMock(return_value={"sources": [], "insights": []}),
        ),
    ):
        prompter.return_value.render.return_value = "Help with the supplied material."
        result = node(
            {"messages": [user], "source_id": "source:one"},
            {"configurable": {"model_id": "model:vision"}},
        )
    assert result["messages"].content == "A red image"
    payload = model.invoke.call_args.args[0]
    assert payload[-1].content[-1]["image_url"]["url"] == image.data_url
    context = provision.call_args.args[0]
    assert "What is shown?" in context
    assert image.data_url not in context
    assert provision.call_args.args[1] == "model:vision"


def test_text_only_context_remains_available():
    assert (
        chat_model_context(
            [SystemMessage(content="Instructions"), HumanMessage(content="Hello")]
        )
        == "system: Instructions\nhuman: Hello"
    )
    assert build_user_message("Hello", []).content == "Hello"


@pytest.mark.parametrize("source_chat", [False, True])
def test_both_apis_accept_image_only_turns(source_chat):
    from api.main import app
    from api.routers import chat
    from api.routers import source_chat as source

    module = source if source_chat else chat
    session = SimpleNamespace(model_override=None, save=AsyncMock())
    captured = []

    def invoke(graph, state, config, user):
        captured.append(user)
        return {"messages": [user, AIMessage(content="A red image", id="reply")]}

    graph = source.source_chat_graph if source_chat else chat.chat_graph
    with (
        patch.object(
            chat,
            "get_session_or_404",
            new=AsyncMock(return_value=("chat_session:one", session)),
        ),
        patch.object(
            source,
            "get_verified_source_session",
            new=AsyncMock(
                return_value=("source:one", None, "chat_session:one", session)
            ),
        ),
        patch.object(chat, "repo_query", new=AsyncMock(return_value=[])),
        patch.object(graph, "get_state", return_value=SimpleNamespace(values={})),
        patch.object(module, "invoke_chat_turn", side_effect=invoke),
    ):
        client = TestClient(app)
        url = (
            "/api/sources/source:one/chat/sessions/chat_session:one/messages"
            if source_chat
            else "/api/chat/execute"
        )
        response = client.post(
            url,
            json={
                "session_id": "chat_session:one",
                "context": {},
                "images": [_image()],
            },
        )
    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].content[0]["type"] == "image_url"
    if not source_chat:
        assert response.json()["messages"][0]["images"][0] == _image()
    else:
        assert '"type": "complete"' in response.text


@pytest.mark.parametrize(
    "url,payload",
    [
        ("/api/chat/execute", {"session_id": "one", "context": {}}),
        ("/api/sources/one/chat/sessions/one/messages", {}),
    ],
)
def test_api_rejects_invalid_images_before_invoking_model(url, payload):
    from api.main import app

    response = TestClient(app).post(
        url,
        json={
            **payload,
            "message": "hello",
            "images": [{"name": "x", "data_url": "https://example.com/x.png"}],
        },
    )
    assert response.status_code == 422


def test_unsupported_vision_error_explains_model_selection():
    error_type, message = classify_error(
        ValueError("This model does not support image inputs")
    )
    assert error_type is InvalidInputError
    assert "vision-capable" in message
