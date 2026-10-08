import base64
from io import BytesIO
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from PIL import Image

from open_notebook.domain.notebook import Asset, Source
from open_notebook.exceptions import ConfigurationError, InvalidInputError
from open_notebook.utils import source_images
from open_notebook.utils.chat_images import message_images
from open_notebook.utils.chat_visuals import invoke_visual_chat


@pytest.fixture
def image_source(tmp_path, monkeypatch):
    monkeypatch.setattr(source_images, "UPLOADS_FOLDER", str(tmp_path))
    image = Image.new("RGB", (200, 100), "red")
    image.paste("blue", (100, 0, 200, 100))
    path = tmp_path / "figure.png"
    image.save(path)
    source = Source(title="Figure", asset=Asset(file_path=str(path)))
    object.__setattr__(source, "id", "source:one")
    return source


def test_actual_source_crop_and_provenance(image_source):
    image = source_images.render_source_image(image_source, 1, [0.5, 0, 1, 1])
    cropped = Image.open(BytesIO(base64.b64decode(image.data_url.split(",")[1])))
    assert cropped.size == (100, 100)
    assert cropped.getpixel((20, 20)) == (0, 0, 255)
    assert image.source_id == "source:one"
    assert image.source_title == "Figure"
    assert image.page == 1
    assert image.kind == "source"


@pytest.mark.parametrize(
    "box",
    [[0, 0, 0, 1], [-1, 0, 1, 1], [0, 0, 1], [0.9, 0, 0.1, 1], [float("nan"), 0, 1, 1]],
)
def test_invalid_crop_rejected(image_source, box):
    with pytest.raises(InvalidInputError):
        source_images.render_source_image(image_source, 1, box)


def test_pdf_render_works_without_native_text(image_source):
    path = image_source.asset.file_path.replace(".png", ".pdf")
    with Image.open(image_source.asset.file_path) as image:
        image.save(path, "PDF", save_all=True, append_images=[image])
    image_source.asset.file_path = path
    info = source_images.inspect_source(image_source)
    assert info["pages"] == 2
    assert info["matches"][0]["text"] == ""
    crop = source_images.render_source_image(image_source, 2, [0.5, 0, 1, 1])
    assert crop.page == 2
    with pytest.raises(InvalidInputError):
        source_images.render_source_image(image_source, 3)


def test_file_containment_and_missing_file(image_source, tmp_path):
    image_source.asset.file_path = str(tmp_path.parent / "outside.png")
    with pytest.raises(InvalidInputError, match="outside"):
        source_images.source_file(image_source)
    image_source.asset.file_path = str(tmp_path / "missing.png")
    with pytest.raises(InvalidInputError, match="Re-upload"):
        source_images.source_file(image_source)


class ToolModel:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.payloads = []

    def bind_tools(self, tools):
        self.tool_names = [tool.name for tool in tools]
        return self

    async def ainvoke(self, messages):
        self.payloads.append(list(messages))
        return next(self.replies)


def call(name, args, identifier):
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": identifier}]
    )


@pytest.mark.asyncio
async def test_preview_crop_answer_and_saved_images(image_source, monkeypatch):
    monkeypatch.setattr(Source, "get", AsyncMock(return_value=image_source))
    model = ToolModel(
        [
            call(
                "preview_source_page", {"source_id": "source:one", "page": 1}, "preview"
            ),
            call(
                "crop_source_image",
                {
                    "source_id": "source:one",
                    "page": 1,
                    "box": [0.5, 0, 1, 1],
                    "caption": "Blue area",
                },
                "crop",
            ),
            AIMessage(content="Here is the blue region."),
        ]
    )
    reply = await invoke_visual_chat(
        model, [HumanMessage(content="Show a crop")], {"source:one"}, None
    )
    images = message_images(reply)
    assert len(images) == 1
    assert images[0].name == "Blue area"
    assert images[0].kind == "source"
    assert reply.content == "Here is the blue region.\n\n[[image:1]]"
    assert not reply.tool_calls
    assert any(isinstance(item.content, list) for item in model.payloads[1])
    # The saved AI text contains neither tool internals nor page preview bytes.
    assert "data:" not in reply.content


@pytest.mark.asyncio
async def test_excluded_source_is_not_read(image_source, monkeypatch):
    get = AsyncMock(return_value=image_source)
    monkeypatch.setattr(Source, "get", get)
    model = ToolModel(
        [
            call(
                "preview_source_page",
                {"source_id": "source:excluded", "page": 1},
                "bad",
            ),
            AIMessage(content="Source is not selected."),
        ]
    )
    reply = await invoke_visual_chat(model, [], {"source:one"}, None)
    get.assert_not_awaited()
    assert not message_images(reply)
    assert "Tool error" in model.payloads[-1][-1].content


@pytest.mark.asyncio
async def test_crop_requires_preview(image_source, monkeypatch):
    get = AsyncMock(return_value=image_source)
    monkeypatch.setattr(Source, "get", get)
    model = ToolModel(
        [
            call(
                "crop_source_image",
                {
                    "source_id": "source:one",
                    "page": 1,
                    "box": [0, 0, 1, 1],
                    "caption": "Invented",
                },
                "bad",
            ),
            AIMessage(content="Need a preview."),
        ]
    )
    reply = await invoke_visual_chat(model, [], {"source:one"}, None)
    get.assert_not_awaited()
    assert not message_images(reply)


@pytest.mark.asyncio
async def test_multiple_tools_receive_results_before_image_preview(
    image_source, monkeypatch
):
    monkeypatch.setattr(Source, "get", AsyncMock(return_value=image_source))
    multiple = call("preview_source_page", {"source_id": "source:one", "page": 1}, "p1")
    multiple.tool_calls.append(
        {
            "name": "inspect_source_pages",
            "args": {"source_id": "source:one"},
            "id": "p2",
            "type": "tool_call",
        }
    )
    model = ToolModel([multiple, AIMessage(content="Done")])
    await invoke_visual_chat(model, [], {"source:one"}, None)
    history = model.payloads[-1]
    assert isinstance(history[-3], ToolMessage)
    assert isinstance(history[-2], ToolMessage)
    assert isinstance(history[-1], HumanMessage)


@pytest.mark.asyncio
async def test_generation_only_once_and_persisted_metadata(image_source, monkeypatch):
    import open_notebook.utils.chat_visuals as visuals

    image = source_images.render_source_image(image_source, 1)
    image.kind = "generated"
    image.source_id = image.source_title = image.page = None
    generate = AsyncMock(return_value=image)
    monkeypatch.setattr(visuals, "generate_chat_image", generate)
    model = ToolModel(
        [
            call("generate_image", {"prompt": "A diagram", "caption": "Diagram"}, "g1"),
            call("generate_image", {"prompt": "Again", "caption": "Another"}, "g2"),
            AIMessage(content="Generated illustration."),
        ]
    )
    reply = await invoke_visual_chat(model, [], set(), "model:one")
    generate.assert_awaited_once_with("A diagram", "Diagram", "model:one")
    assert message_images(reply)[0].kind == "generated"
    assert "Tool error" in model.payloads[-1][-1].content


@pytest.mark.asyncio
async def test_unsupported_tool_model_clear_error():
    with pytest.raises(ConfigurationError, match="tool calling"):
        await invoke_visual_chat(SimpleNamespace(), [], set(), None)


@pytest.mark.asyncio
async def test_image_adapter_uses_linked_credentials(image_source, monkeypatch):
    import open_notebook.ai.image_generation as adapter

    image = source_images.render_source_image(image_source, 1)
    response = SimpleNamespace(
        data=[SimpleNamespace(b64_json=image.data_url.split(",")[1])]
    )
    sdk = AsyncMock()
    sdk.__aenter__.return_value = sdk
    sdk.images.generate.return_value = response

    def constructor(**kwargs):
        return sdk

    monkeypatch.setattr(adapter, "AsyncOpenAI", constructor)
    for variable in [
        "OPEN_NOTEBOOK_IMAGE_CREDENTIAL_ID",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPEN_NOTEBOOK_IMAGE_MODEL",
    ]:
        monkeypatch.delenv(variable, raising=False)
    credential = SimpleNamespace(to_esperanto_config=lambda: {"api_key": "test"})
    model = SimpleNamespace(
        provider="openai",
        credential="credential:one",
        get_credential_obj=AsyncMock(return_value=credential),
    )
    monkeypatch.setattr(adapter.Model, "get", AsyncMock(return_value=model))
    result = await adapter.generate_chat_image("An image", "Caption", "model:one")
    assert result.kind == "generated"
    sdk.images.generate.assert_awaited_once_with(
        model="gpt-image-1.5",
        prompt="An image",
        size="1024x1024",
        quality="low",
        output_format="png",
        n=1,
    )


def test_ai_image_checkpoint_roundtrip(image_source, tmp_path):
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph

    from open_notebook.graphs.chat import ThreadState

    image = source_images.render_source_image(image_source, 1)
    reply = AIMessage(
        content="A source figure",
        additional_kwargs={"response_images": [image.model_dump()]},
    )
    with SqliteSaver.from_conn_string(str(tmp_path / "checkpoint.db")) as saver:
        graph = StateGraph(ThreadState)
        graph.add_node("reply", lambda state: {"messages": reply})
        graph.add_edge(START, "reply")
        graph.add_edge("reply", END)
        compiled = graph.compile(checkpointer=saver)
        config = RunnableConfig(configurable={"thread_id": "visual"})
        state = ThreadState(
            messages=[],
            notebook=None,
            context=None,
            context_config=None,
            model_override=None,
        )
        compiled.invoke(cast(Any, state), config)
        restored = compiled.get_state(config).values["messages"][-1]
        assert message_images(restored) == [image]


@pytest.mark.parametrize(
    "image_link",
    ["attachment:image1", "attachment-image-1", "https://example.com/invented.png"],
)
def test_nonexistent_attachment_links_removed_without_changing_real_citations(
    image_link,
):
    from open_notebook.utils.chat_visuals import _visual_reply

    reply = AIMessage(
        content=f"A figure [source:one].\n![Crop]({image_link})\n[Existing](https://example.com/figure.png)"
    )
    cleaned = _visual_reply(reply, [])
    assert "![Crop]" not in cleaned.content
    assert "[source:one]" in cleaned.content
    assert "https://example.com/figure.png" in cleaned.content


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["gpt-6-luna", "gpt-6-sol", "gpt-6.1-sol"])
async def test_gpt6_tools_use_responses_and_preserve_reasoning(name):
    import json

    import httpx
    from langchain_openai import ChatOpenAI

    from open_notebook.utils.chat_visuals import _prepare_tool_model

    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "model": name,
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_test",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": "Done", "annotations": []}
                        ],
                    }
                ],
                "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        original = ChatOpenAI(
            model=name, api_key="test", http_async_client=client, reasoning_effort="low"
        )
        model = _prepare_tool_model(original)
        await model.bind_tools(
            [
                {
                    "name": "inspect",
                    "description": "Inspect",
                    "parameters": {"type": "object", "properties": {}},
                }
            ]
        ).ainvoke([HumanMessage(content="Inspect")])
    assert requests[0].url.path == "/v1/responses"
    body = json.loads(requests[0].content)
    assert body["reasoning"] == {"effort": "low"}
    assert body["store"] is False
    assert "reasoning.encrypted_content" in body["include"]
    assert body["tools"][0]["name"] == "inspect"
    assert original.use_responses_api is None
    assert original.reasoning_effort == "low"


def test_other_models_keep_their_transport():
    from langchain_openai import ChatOpenAI

    from open_notebook.utils.chat_visuals import _prepare_tool_model

    model = ChatOpenAI(model="gpt-4.1", api_key="test")
    assert _prepare_tool_model(model) is model
