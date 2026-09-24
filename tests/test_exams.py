from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api import exam_service
from open_notebook.domain.exam import Exam, ExamAttempt, ExamQuestion, QuestionResult
from open_notebook.graphs.exam import (
    GeneratedQuestion,
    normalize_answer,
    validate_generated_questions,
)


def _questions() -> list[ExamQuestion]:
    return [
        ExamQuestion(
            id="q1",
            type="multiple_choice",
            prompt="Capital of France?",
            options=["Rome", "Paris", "Madrid", "Berlin"],
            correct_option=1,
        ),
        ExamQuestion(
            id="q2",
            type="fill_blank",
            prompt="Water boils at ___ degrees and freezes at ___ degrees.",
            blanks=[["100", "cien"], ["0", "cero"]],
            points=2,
        ),
        ExamQuestion(
            id="q3",
            type="open",
            prompt="Explain photosynthesis.",
            reference_answer="Plants turn light into chemical energy.",
            rubric="Light, CO2, glucose.",
            points=5,
        ),
    ]


def _exam() -> Exam:
    return Exam(
        id="exam:1",
        notebook_id="notebook:1",
        title="Test exam",
        questions=[q.model_dump() for q in _questions()],
        created=datetime(2026, 1, 1),
        updated=datetime(2026, 1, 1),
    )


def test_normalize_answer_ignores_case_accents_and_punctuation():
    assert normalize_answer("  Fotosíntesis. ") == normalize_answer("fotosintesis")
    assert normalize_answer("Río   de la Plata") == "rio de la plata"


def test_validate_generated_questions_drops_malformed_and_numbers_ids():
    generated = [
        GeneratedQuestion(
            type="multiple_choice", prompt="ok?", options=["a", "b"], correct_option=0
        ),
        GeneratedQuestion(
            type="multiple_choice",
            prompt="bad index",
            options=["a", "b"],
            correct_option=5,
        ),
        GeneratedQuestion(type="fill_blank", prompt="no marker", blanks=[["x"]]),
        GeneratedQuestion(
            type="fill_blank", prompt="A _____ b", blanks=[["x"], ["extra"]]
        ),
        GeneratedQuestion(
            type="open", prompt="Why?", reference_answer="Because", points=0
        ),
    ]
    questions = validate_generated_questions(generated)
    assert [q.id for q in questions] == ["q1", "q2", "q3"]
    assert questions[1].prompt == "A ___ b"
    assert questions[1].blanks == [["x"]]
    assert questions[2].points == 1.0


def _auto(question: ExamQuestion, answer) -> QuestionResult:
    result = exam_service.grade_deterministic(question, answer)
    assert result is not None
    return result


def test_grade_deterministic_multiple_choice():
    mc = _questions()[0]
    assert _auto(mc, 1).is_correct
    assert _auto(mc, "1").score == 1
    assert _auto(mc, 0).score == 0
    assert _auto(mc, None).score == 0


def test_grade_deterministic_fill_blank():
    fb = _questions()[1]
    assert _auto(fb, ["100", "Cero"]).score == 2
    assert _auto(fb, ["", ""]).score == 0
    # A non-matching answer needs the model.
    assert exam_service.grade_deterministic(fb, ["cien grados", "0"]) is None


def test_grade_deterministic_open_needs_ai_unless_empty():
    op = _questions()[2]
    assert _auto(op, "  ").score == 0
    assert exam_service.grade_deterministic(op, "Light energy") is None


@pytest.mark.asyncio
async def test_grade_attempt_uses_ai_only_for_free_answers():
    grade_ai = AsyncMock(return_value=(3.0, "Missing CO2."))
    with (
        patch("api.exam_service.grade_with_ai", grade_ai),
        patch.object(ExamAttempt, "save", new_callable=AsyncMock),
    ):
        attempt = await exam_service.grade_attempt(
            _exam(), {"q1": 1, "q2": ["100", "0"], "q3": "Light to energy"}
        )
    grade_ai.assert_awaited_once()
    assert attempt.score == 1 + 2 + 3
    assert attempt.max_score == 8
    by_id = {r["question_id"]: r for r in attempt.results}
    assert by_id["q3"]["graded_by"] == "ai"
    assert by_id["q3"]["feedback"] == "Missing CO2."
    assert by_id["q1"]["graded_by"] == "auto"


def test_get_exam_hides_answer_key_unless_requested():
    from api.main import app

    client = TestClient(app)
    with (
        patch.object(Exam, "get", new_callable=AsyncMock, return_value=_exam()),
        patch("api.routers.exams.repo_query", new_callable=AsyncMock, return_value=[]),
    ):
        hidden = client.get("/api/exams/exam:1").json()
        shown = client.get("/api/exams/exam:1?include_answers=true").json()

    assert hidden["question_count"] == 3
    assert hidden["max_score"] == 8
    assert hidden["questions"][0]["correct_option"] is None
    assert hidden["questions"][1]["blanks"] is None
    assert hidden["questions"][1]["blank_count"] == 2
    assert shown["questions"][0]["correct_option"] == 1
    assert shown["questions"][2]["reference_answer"]


@pytest.mark.asyncio
async def test_invoke_structured_retries_once_on_malformed_json():
    from langchain_core.exceptions import OutputParserException
    from langchain_core.output_parsers.pydantic import PydanticOutputParser

    from open_notebook.graphs.exam import GradeOutput, _invoke_structured

    class Reply:
        def __init__(self, content):
            self.content = content

    parser: PydanticOutputParser[GradeOutput] = PydanticOutputParser(
        pydantic_object=GradeOutput
    )
    model = AsyncMock()
    model.ainvoke.side_effect = [
        Reply("not json"),
        Reply('{"score": 2, "feedback": "ok"}'),
    ]
    grade = await _invoke_structured(model, "prompt", parser)
    assert grade.score == 2 and model.ainvoke.await_count == 2

    model = AsyncMock()
    model.ainvoke.return_value = Reply("still not json")
    with pytest.raises(OutputParserException):
        await _invoke_structured(model, "prompt", parser)
    assert model.ainvoke.await_count == 2


def test_validate_multiple_select_questions():
    generated = [
        GeneratedQuestion(
            type="multiple_select",
            prompt="Pick primes",
            options=["2", "3", "4", "6"],
            correct_options=[1, 0, 1],
            points=2,
        ),
        # One correct option: downgraded to a plain multiple-choice question.
        GeneratedQuestion(
            type="multiple_select",
            prompt="Pick even",
            options=["1", "2", "3"],
            correct_options=[1],
        ),
        GeneratedQuestion(
            type="multiple_select",
            prompt="Out of range",
            options=["a", "b", "c"],
            correct_options=[0, 7],
        ),
        GeneratedQuestion(
            type="multiple_select",
            prompt="Too few options",
            options=["a", "b"],
            correct_options=[0, 1],
        ),
    ]
    questions = validate_generated_questions(generated)
    assert len(questions) == 2
    assert questions[0].type == "multiple_select"
    assert questions[0].correct_options == [0, 1]
    assert questions[1].type == "multiple_choice"
    assert questions[1].correct_option == 1


def test_grade_deterministic_multiple_select_partial_credit():
    ms = ExamQuestion(
        id="q1",
        type="multiple_select",
        prompt="Pick primes",
        options=["2", "3", "4", "5"],
        correct_options=[0, 1, 3],
        points=3,
    )
    assert _auto(ms, [0, 1, 3]).is_correct
    assert _auto(ms, ["3", "0"]).score == 2  # 2 of 3 correct, no wrong picks
    assert _auto(ms, [0, 1, 2]).score == 1  # 2 correct - 1 wrong
    assert _auto(ms, [0, 1, 2, 3]).score == 2  # selecting everything is penalised
    assert _auto(ms, [2]).score == 0
    assert _auto(ms, None).score == 0
    assert _auto(ms, [0, 1, 3]).graded_by == "auto"
