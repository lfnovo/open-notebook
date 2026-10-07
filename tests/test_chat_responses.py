import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from api.routers import chat_quizzes
from api.routers._chat_shared import extract_chat_messages
from open_notebook.domain.chat_quiz import ChatQuiz, ChatQuizAttempt
from open_notebook.exceptions import ExternalServiceError
from open_notebook.utils import chat_responses
from open_notebook.utils.chat_images import ChatImage
from open_notebook.utils.chat_visuals import _visual_reply


@pytest.fixture(autouse=True)
def disable_real_repairs(monkeypatch):
    repair = AsyncMock(side_effect=ExternalServiceError("Repair service unavailable"))
    monkeypatch.setattr(chat_responses, "repair_inline_quiz", repair)
    return repair


def payload(**changes):
    data = {
        "title": "Practice",
        "language": "es",
        "questions": [
            {
                "type": "multiple_choice",
                "prompt": "Pick the even number",
                "options": ["3", "4"],
                "correct_option": 1,
                "explanation": "4 is divisible by 2",
            }
        ],
    }
    data.update(changes)
    return data


def reply(data):
    return AIMessage(
        id="ai:one",
        content="Before\n\n```chat-quiz\n" + json.dumps(data) + "\n```\n\nAfter",
    )


@pytest.mark.asyncio
async def test_quiz_is_positioned_and_keys_are_private(monkeypatch):
    saved = []

    async def save(quiz):
        quiz.id = "chat_quiz:test"
        saved.append(quiz)

    monkeypatch.setattr(ChatQuiz, "save", save)
    result = await chat_responses.materialize_chat_response(
        reply(payload()), "chat_session:one", "model:one"
    )
    assert (
        result.content.index("Before")
        < result.content.index("[[quiz:chat_quiz:test]]")
        < result.content.index("After")
    )
    assert "correct_option" not in result.content
    assert "divisible" not in result.content
    assert saved[0].questions[0]["correct_option"] == 1
    exposed = extract_chat_messages([result])[0].model_dump()
    assert exposed["quizzes"] == ["chat_quiz:test"]
    assert "correct_option" not in json.dumps(exposed)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content", ["```chat-quiz\n{bad}\n```", "```chat-quiz\n{}", "```CHAT-QUIZ\n{}\n```"]
)
async def test_invalid_quizzes_never_leak_keys_or_save(content, monkeypatch):
    save = AsyncMock()
    monkeypatch.setattr(ChatQuiz, "save", save)
    result = await chat_responses.materialize_chat_response(
        AIMessage(content=content), "chat_session:one", "model:one"
    )
    assert result.content == "[[quiz-unavailable]]"
    assert "chat-quiz" not in result.content
    save.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_figure_rejected_and_only_one_quiz_per_turn(monkeypatch):
    save = AsyncMock()
    monkeypatch.setattr(ChatQuiz, "save", save)
    data = payload()
    data["questions"][0]["image_ids"] = ["figure9"]
    result = await chat_responses.materialize_chat_response(
        reply(data), "chat_session:one", "model:one"
    )
    assert "Before" in result.content and "After" in result.content
    assert "[[quiz-unavailable]]" in result.content
    assert "figure9" not in result.content
    message = reply(payload())
    multiple = await chat_responses.materialize_chat_response(
        AIMessage(content=message.content * 2), "chat_session:one", "model:one"
    )
    assert "correct_option" not in multiple.content
    save.assert_not_awaited()


@pytest.mark.asyncio
async def test_ordinary_response_unchanged_and_invented_quiz_id_removed():
    message = AIMessage(content="Text only")
    assert (
        await chat_responses.materialize_chat_response(
            message, "chat_session:one", None
        )
    ).content == "Text only"
    fake = AIMessage(content="Text [[quiz:chat_quiz:fake]]")
    assert (
        "fake"
        not in (
            await chat_responses.materialize_chat_response(
                fake, "chat_session:one", None
            )
        ).content
    )


@pytest.mark.asyncio
async def test_quiz_endpoint_hides_keys_until_attempt(monkeypatch):
    quiz = ChatQuiz(
        id="chat_quiz:one",
        session_id="chat_session:one",
        title="Practice",
        questions=[{"id": "q1", **payload()["questions"][0]}],
    )
    monkeypatch.setattr(
        chat_quizzes.ChatSession, "get", AsyncMock(return_value=SimpleNamespace())
    )
    attempts = AsyncMock(return_value=[])
    monkeypatch.setattr(ChatQuiz, "get_attempts", attempts)
    hidden = await chat_quizzes._response(quiz)
    assert hidden.questions[0].correct_option is None
    assert hidden.review_questions is None
    attempts.return_value = [
        ChatQuizAttempt(
            id="chat_quiz_attempt:one",
            exam_id="chat_quiz:one",
            answers={"q1": 1},
            score=1,
            max_score=1,
        )
    ]
    shown = await chat_quizzes._response(quiz)
    assert shown.latest_attempt is not None
    assert shown.review_questions is not None
    assert shown.latest_attempt.score == 1
    assert shown.review_questions[0].correct_option == 1


def test_images_resolve_real_ids_at_their_position():
    image = cast(ChatImage, SimpleNamespace(model_dump=lambda: {"name": "Figure"}))
    result = _visual_reply(
        AIMessage(
            content="Before\n\n[[image:1]]\n\nAfter ![Fake](https://fake/image.png) [[image:9]]"
        ),
        [image],
    )
    assert (
        result.content.index("Before")
        < result.content.index("[[image:1]]")
        < result.content.index("After")
    )
    assert "fake" not in result.content.lower()
    assert "[[image:9]]" not in result.content


def test_old_attachment_markdown_resolves_in_place():
    image = cast(ChatImage, SimpleNamespace(model_dump=lambda: {}))
    result = _visual_reply(
        AIMessage(content="Before ![Figure](attachment:image1) After"), [image]
    )
    assert (
        result.content.index("Before")
        < result.content.index("[[image:1]]")
        < result.content.index("After")
    )


@pytest.mark.asyncio
async def test_session_deletion_cascades_with_nonreserved_sql_parameters(monkeypatch):
    import open_notebook.domain.notebook as notebook_domain
    from open_notebook.domain.base import ObjectModel

    queries = AsyncMock(return_value=[])
    monkeypatch.setattr(notebook_domain, "repo_query", queries)
    remove = AsyncMock(return_value=True)
    monkeypatch.setattr(ObjectModel, "delete", remove)
    session = notebook_domain.ChatSession(id="chat_session:one")
    assert await session.delete()
    assert queries.await_count == 2
    assert "DELETE chat_quiz_attempt" in queries.call_args_list[0].args[0]
    assert "DELETE chat_quiz WHERE" in queries.call_args_list[1].args[0]
    for call in queries.call_args_list:
        assert "$quiz_session_id" in call.args[0]
        assert "session" not in call.args[1]
    remove.assert_awaited_once()


@pytest.mark.asyncio
async def test_malformed_test_is_repaired_in_place(monkeypatch, disable_real_repairs):
    disable_real_repairs.side_effect = None
    disable_real_repairs.return_value = chat_responses.InlineQuiz.model_validate(
        payload()
    )

    async def save(quiz):
        quiz.id = "chat_quiz:repaired"

    monkeypatch.setattr(ChatQuiz, "save", save)
    result = await chat_responses.materialize_chat_response(
        AIMessage(
            content='Before\n```chat-quiz\n{"title":"Practice", bad}\n```\nAfter'
        ),
        "chat_session:one",
        "model:one",
    )
    assert (
        result.content.index("Before")
        < result.content.index("[[quiz:chat_quiz:repaired]]")
        < result.content.index("After")
    )
    assert result.additional_kwargs["response_quizzes"] == ["chat_quiz:repaired"]
    assert "bad" not in result.content
    disable_real_repairs.assert_awaited_once()


@pytest.mark.asyncio
async def test_inline_and_crlf_fences_work_without_repair(
    monkeypatch, disable_real_repairs
):
    async def save(quiz):
        quiz.id = "chat_quiz:one"

    monkeypatch.setattr(ChatQuiz, "save", save)
    for content in [
        "```chat-quiz " + json.dumps(payload()) + "```",
        "```chat-quiz\r\n" + json.dumps(payload()) + "\r\n```",
    ]:
        result = await chat_responses.materialize_chat_response(
            AIMessage(content=content), "chat_session:one", "model:one"
        )
        assert result.additional_kwargs["response_quizzes"] == ["chat_quiz:one"]
    disable_real_repairs.assert_not_awaited()


@pytest.mark.asyncio
async def test_truncated_test_failure_preserves_prose_and_hides_keys():
    result = await chat_responses.materialize_chat_response(
        AIMessage(
            content='Explanation\n```chat-quiz\n{"correct_option":1, "reference_answer":"PRIVATE"'
        ),
        "chat_session:one",
        "model:one",
    )
    assert "Explanation" in result.content and "[[quiz-unavailable]]" in result.content
    assert "PRIVATE" not in result.content and "correct_option" not in result.content


@pytest.mark.asyncio
async def test_repair_uses_selected_model_and_structured_output(monkeypatch):
    from open_notebook.graphs import chat_quiz as graph

    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content=json.dumps(payload()))
    provision = AsyncMock(return_value=model)
    monkeypatch.setattr(graph, "provision_langchain_model", provision)
    recovered = await graph.repair_inline_quiz(
        "malformed original test", {}, "model:selected"
    )
    assert recovered.questions[0].correct_option == 1
    assert provision.call_args.args[1] == "model:selected"
    assert provision.call_args.kwargs["structured"] == {"type": "json"}
    assert model.ainvoke.call_args.args[0][1].content == "malformed original test"


@pytest.mark.parametrize(
    ("prompt_text", "expected"),
    [
        ("Generá una imagen de los vecinos KNN", (True, False)),
        ("Haceme un examen de KNN", (False, True)),
        ("Un cuestionario con imágenes", (True, True)),
        ("Explicame KNN sin imágenes ni test", (False, False)),
        ("Explicame KNN", (False, False)),
    ],
)
def test_explicit_widget_requests(prompt_text, expected):
    assert chat_responses.requested_widgets(prompt_text) == expected


@pytest.mark.asyncio
async def test_plain_exam_becomes_interactive_without_exposing_answers(monkeypatch):
    from open_notebook.graphs.chat_quiz import InlineQuiz

    repair = AsyncMock(return_value=InlineQuiz.model_validate(payload()))
    monkeypatch.setattr(chat_responses, "repair_inline_quiz", repair)

    async def save(quiz):
        quiz.id = "chat_quiz:requested"

    monkeypatch.setattr(ChatQuiz, "save", save)
    result = await chat_responses.materialize_chat_response(
        AIMessage(content="1. Pick an even number. Correct answer: 4"),
        "chat_session:test",
        "model:test",
        "Haceme un examen",
        "Even numbers divide by 2",
    )
    assert result.content == "[[quiz:chat_quiz:requested]]"
    assert result.additional_kwargs["response_quizzes"] == ["chat_quiz:requested"]
    assert "Even numbers divide by 2" in repair.call_args.args[0]
    assert "Correct answer" not in result.content
