import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from PIL import Image

from api import exam_service
from api.routers.exams import _exam_response
from open_notebook.domain.exam import Exam, ExamQuestion
from open_notebook.exceptions import InvalidInputError
from open_notebook.graphs import exam as graph
from open_notebook.utils.chat_images import ChatImage


@pytest.fixture
def figure():
    buffer = BytesIO()
    Image.new("RGB", (30, 20), "blue").save(buffer, "PNG")
    return ChatImage(
        name="Answer-revealing caption",
        data_url="data:image/png;base64,"
        + base64.b64encode(buffer.getvalue()).decode(),
        kind="source",
        source_id="source:one",
        source_title="Solutions.pdf",
        page=2,
    )


def test_api_shares_pool_and_hides_caption_until_review(figure):
    question = ExamQuestion(
        id="q1",
        type="open",
        prompt="Interpret Figure 1",
        image_ids=["figure1"],
        reference_answer="Blue",
    )
    exam = Exam(
        id="exam:one",
        notebook_id="notebook:one",
        title="Visual",
        images={"figure1": figure},
        questions=[
            question.model_dump(),
            question.model_copy(update={"id": "q2"}).model_dump(),
        ],
    )
    hidden = _exam_response(exam, include_questions=True).model_dump()
    shown = _exam_response(
        exam, include_questions=True, include_answers=True
    ).model_dump()
    assert hidden["questions"][0]["image_ids"] == ["figure1"]
    assert len(hidden["images"]) == 1
    assert hidden["images"]["figure1"]["name"] == "figure1"
    assert "source_title" not in hidden["images"]["figure1"]
    assert hidden["questions"][0]["reference_answer"] is None
    assert shown["images"]["figure1"]["source_title"] == "Solutions.pdf"
    assert shown["questions"][0]["reference_answer"] == "Blue"
    assert _exam_response(exam).images == {}
    assert Exam(notebook_id="notebook:one", title="Legacy").images == {}


def test_missing_figure_questions_are_rejected(figure):
    questions = [
        graph.GeneratedQuestion(
            type="open", prompt="Missing", image_ids=["invented"], reference_answer="X"
        ),
        graph.GeneratedQuestion(
            type="open", prompt="Valid", image_ids=["figure1"], reference_answer="Blue"
        ),
        graph.GeneratedQuestion(type="open", prompt="Text", reference_answer="Y"),
    ]
    valid = graph.validate_generated_questions(questions, {"figure1": figure})
    assert [q.prompt for q in valid] == ["Valid", "Text"]


@pytest.mark.asyncio
async def test_generation_and_grading_receive_actual_pixels(figure, monkeypatch):
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(
        content='{"title":"Visual","questions":[{"type":"open","prompt":"Describe Figure 1","image_ids":["figure1"],"reference_answer":"Blue"}]}'
    )
    provision = AsyncMock(return_value=model)
    monkeypatch.setattr(graph, "provision_langchain_model", provision)
    _, questions = await graph.generate_exam_questions(
        "Study material",
        num_multiple_choice=0,
        num_multiple_select=0,
        num_fill_blank=0,
        num_open=1,
        difficulty="medium",
        language="es",
        instructions=None,
        model_id=None,
        images={"figure1": figure},
    )
    payload = model.ainvoke.call_args.args[0]
    assert payload[-1].content[1]["image_url"]["url"] == figure.data_url
    assert figure.data_url not in provision.call_args.args[0]
    assert questions[0].image_ids == ["figure1"]
    model.ainvoke.return_value = AIMessage(content='{"score":1,"feedback":"Correct"}')
    assert await graph.grade_with_ai(
        questions[0], "Blue", language="es", model_id=None, images={"figure1": figure}
    ) == (1, "Correct")
    assert (
        model.ainvoke.call_args.args[0][-1].content[1]["image_url"]["url"]
        == figure.data_url
    )
    with pytest.raises(InvalidInputError, match="unavailable"):
        await graph.grade_with_ai(questions[0], "Blue", language="es", model_id=None)


@pytest.mark.asyncio
@pytest.mark.parametrize("include_images", [True, False])
async def test_creation_can_disable_images_and_discards_unused_pool(
    figure, monkeypatch, include_images
):
    notebook = SimpleNamespace(name="Notebook")
    monkeypatch.setattr(exam_service.Notebook, "get", AsyncMock(return_value=notebook))
    monkeypatch.setattr(
        exam_service,
        "build_study_material",
        AsyncMock(return_value=("Material", ["source:allowed"])),
    )
    collector = AsyncMock(return_value={"figure1": figure, "figure2": figure})
    monkeypatch.setattr(exam_service, "collect_exam_images", collector)
    question = ExamQuestion(
        id="q1",
        type="open",
        prompt="Describe",
        reference_answer="Blue",
        image_ids=["figure1"] if include_images else [],
    )
    generator = AsyncMock(return_value=("Visual", [question]))
    monkeypatch.setattr(exam_service, "generate_exam_questions", generator)
    monkeypatch.setattr(Exam, "save", AsyncMock())
    exam = await exam_service.create_exam(
        notebook_id="notebook:one",
        title=None,
        source_ids=["source:allowed", "source:excluded"],
        include_notes=False,
        num_multiple_choice=0,
        num_multiple_select=0,
        num_fill_blank=0,
        num_open=1,
        difficulty="medium",
        language="es",
        instructions=None,
        model_id=None,
        include_images=include_images,
    )
    if include_images:
        assert collector.call_args.kwargs["source_ids"] == ["source:allowed"]
        assert list(exam.images) == ["figure1"]
    else:
        collector.assert_not_awaited()
        assert generator.call_args.kwargs["images"] == {}
        assert exam.images == {}


@pytest.mark.asyncio
async def test_save_restores_typed_pool_after_database_refresh(figure, monkeypatch):
    import open_notebook.domain.base as base

    exam = Exam(notebook_id="notebook:one", title="Visual", images={"figure1": figure})
    monkeypatch.setattr(
        base,
        "repo_create",
        AsyncMock(
            return_value=[
                {"id": "exam:one", "images": {"figure1": figure.model_dump()}}
            ]
        ),
    )
    await exam.save()
    assert isinstance(exam.images["figure1"], ChatImage)
    assert (
        _exam_response(exam, include_questions=True).images["figure1"].data_url
        == figure.data_url
    )
