"""LLM steps for practice exams: question generation and free-answer grading.

Deterministic grading (multiple choice, exact fill-in-the-blank matches) lives
in `api/exam_service.py`; only the parts that need a model are here.
"""

import re
import unicodedata
from typing import Any, List, Literal, Optional, TypeVar

from ai_prompter import Prompter
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.ai.models import model_manager
from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.exam import ExamQuestion
from open_notebook.exceptions import (
    ExternalServiceError,
    InvalidInputError,
    OpenNotebookError,
)
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.chat_images import (
    ChatImage,
    chat_model_context,
    message_images,
)
from open_notebook.utils.chat_visuals import invoke_visual_chat
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content

# Reasoning models spend part of this budget thinking; an exam with many open
# questions (reference answer + rubric each) needs a generous output budget.
GENERATE_MAX_TOKENS = 32000
GRADE_MAX_TOKENS = 4096

BLANK_PATTERN = re.compile(r"_{3,}")
# Smaller/local models occasionally return malformed JSON; one retry fixes
# most of those without masking a model that never follows the format.
PARSE_ATTEMPTS = 2

T = TypeVar("T", bound=BaseModel)


class GeneratedQuestion(BaseModel):
    type: Literal["multiple_choice", "multiple_select", "fill_blank", "open"]
    prompt: str
    points: float = 1.0
    image_ids: List[str] = Field(
        default_factory=list,
        max_length=2,
        description="IDs of provided figures essential to answering this question; [] for text-only questions",
    )
    options: List[str] = Field(default_factory=list)
    correct_option: Optional[int] = Field(
        None, description="0-based index of the correct option (multiple_choice)"
    )
    correct_options: List[int] = Field(
        default_factory=list,
        description="0-based indexes of all correct options (multiple_select)",
    )
    blanks: List[List[str]] = Field(
        default_factory=list,
        description="Acceptable answers for each ___ in the prompt, in order (fill_blank)",
    )
    reference_answer: Optional[str] = Field(None, description="Model answer (open)")
    rubric: Optional[str] = Field(None, description="Grading criteria (open)")
    explanation: Optional[str] = None


class GeneratedExam(BaseModel):
    title: str = Field(description="Short title describing the exam topic")
    questions: List[GeneratedQuestion]


class GradeOutput(BaseModel):
    score: float
    feedback: str


async def _invoke_structured(
    model: BaseChatModel, payload: Any, parser: PydanticOutputParser[T]
) -> T:
    for attempt in range(1, PARSE_ATTEMPTS + 1):
        response = await model.ainvoke(payload)
        cleaned = clean_thinking_content(extract_text_content(response.content))
        try:
            return parser.parse(cleaned)
        except OutputParserException:
            if attempt == PARSE_ATTEMPTS:
                raise
            logger.warning("Exam model returned unparseable JSON, retrying once")
    raise AssertionError("unreachable")


def normalize_answer(text: str) -> str:
    """Case-, accent-, punctuation- and whitespace-insensitive form of an answer."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    no_punct = re.sub(r"[^\w\s]", " ", no_accents.lower())
    return " ".join(no_punct.split())


def validate_generated_questions(
    generated: List[GeneratedQuestion],
    images: Optional[dict[str, ChatImage]] = None,
) -> List[ExamQuestion]:
    """Drop malformed questions and assign stable ids (q1, q2, ...)."""
    questions: List[ExamQuestion] = []
    for q in generated:
        prompt = q.prompt.strip()
        if not prompt or any(
            image_id not in (images or {}) for image_id in q.image_ids
        ):
            continue
        points = q.points if q.points and q.points > 0 else 1.0
        data: dict[str, Any] = dict(
            type=q.type,
            prompt=prompt,
            points=float(points),
            explanation=q.explanation,
            image_ids=list(dict.fromkeys(q.image_ids)),
        )
        if q.type == "multiple_choice":
            options = [o.strip() for o in q.options if o and o.strip()]
            if len(options) < 2 or q.correct_option is None:
                continue
            if not 0 <= q.correct_option < len(options):
                continue
            data.update(options=options, correct_option=q.correct_option)
        elif q.type == "multiple_select":
            options = [o.strip() for o in q.options if o and o.strip()]
            correct = sorted(set(q.correct_options))
            if len(options) < 3 or not correct:
                continue
            if not all(0 <= i < len(options) for i in correct):
                continue
            if len(correct) == 1:
                # A single correct option is just a multiple-choice question.
                data.update(
                    type="multiple_choice", options=options, correct_option=correct[0]
                )
            else:
                data.update(options=options, correct_options=correct)
        elif q.type == "fill_blank":
            markers = len(BLANK_PATTERN.findall(prompt))
            blanks = [[a.strip() for a in b if a and a.strip()] for b in q.blanks]
            blanks = [b for b in blanks if b]
            if markers == 0 or len(blanks) < markers:
                continue
            data.update(
                prompt=BLANK_PATTERN.sub("___", prompt), blanks=blanks[:markers]
            )
        else:
            data.update(reference_answer=q.reference_answer, rubric=q.rubric)
        questions.append(ExamQuestion(id=f"q{len(questions) + 1}", **data))
    return questions


def _figure_blocks(
    images: dict[str, ChatImage], image_ids: Optional[List[str]] = None
) -> list[str | dict[Any, Any]]:
    blocks: list[str | dict[Any, Any]] = []
    for image_id in image_ids if image_ids is not None else images:
        image = images.get(image_id)
        if image is None:
            raise InvalidInputError(f"Question figure {image_id} is unavailable.")
        blocks.extend(
            [
                {
                    "type": "text",
                    "text": f"Figure ID: {image_id}. Inspect the image itself; its caption is not an answer key.",
                },
                {"type": "image_url", "image_url": {"url": image.data_url}},
            ]
        )
    return blocks


async def collect_exam_images(
    content: str,
    *,
    source_ids: List[str],
    language: Optional[str],
    instructions: Optional[str],
    model_id: Optional[str],
    question_count: int,
) -> dict[str, ChatImage]:
    """Choose genuine useful figures before writing image-dependent questions."""
    try:
        if not model_id:
            defaults = await model_manager.get_defaults()
            model_id = (
                defaults.default_transformation_model or defaults.default_chat_model
            )
        prompt = (
            "Prepare visual material for a practice exam, not the questions themselves. "
            "Include images ONLY when students can reason about a chart, diagram, plot, "
            "spatial example or process. Do not add decoration to conceptual/textual exams. "
            "Prefer relevant genuine source crops; generate an educational illustration "
            "only if it is necessary and no suitable source figure is available. "
            "Never use answer sheets, marked answers, solved exercises, rubrics or solutions "
            "as figures. Preview source pages and crop only the useful figure, excluding solutions. "
            "Keep generated figures scientifically accurate, legible, with no correct answers "
            "or question solutions printed on them. All labels must be in the exam language. "
            "Do not invent source diagrams. Finish without attachments if none are useful or "
            "tools cannot obtain suitable figures; the exam will then use standalone text questions. "
            f"Prepare at most {min(4, question_count)} figures. "
            f"Exam language: {language or 'same as the study material'}. "
            f"User exam instructions: {instructions or '(none)'}."
        )
        payload = [
            SystemMessage(content=prompt),
            HumanMessage(
                content=(
                    "Select source figures or generate a new illustration only when necessary for "
                    "an exam on the following study material. Do not provide questions or solutions.\n\n"
                    + content
                )
            ),
        ]
        model = await provision_langchain_model(
            chat_model_context(payload),
            model_id,
            "transformation",
            max_tokens=4096,
        )
        reply = await invoke_visual_chat(model, payload, set(source_ids), model_id)
        return {
            f"figure{index + 1}": image
            for index, image in enumerate(
                message_images(reply)[: min(4, question_count)]
            )
        }
    except OpenNotebookError:
        raise
    except Exception as exc:
        error_class, user_message = classify_error(exc)
        raise error_class(user_message) from exc


async def generate_exam_questions(
    content: str,
    *,
    num_multiple_choice: int,
    num_multiple_select: int,
    num_fill_blank: int,
    num_open: int,
    difficulty: str,
    language: Optional[str],
    instructions: Optional[str],
    model_id: Optional[str],
    images: Optional[dict[str, ChatImage]] = None,
) -> tuple[str, List[ExamQuestion]]:
    """Ask the model for an exam over `content`; returns (title, questions)."""
    try:
        parser: PydanticOutputParser[GeneratedExam] = PydanticOutputParser(
            pydantic_object=GeneratedExam
        )
        # User-supplied instructions are passed as a render variable, never
        # compiled as template source (see docs/7-DEVELOPMENT/security.md).
        system_prompt = Prompter(prompt_template="exam/generate", parser=parser).render(  # type: ignore[arg-type]
            data=dict(
                num_multiple_choice=num_multiple_choice,
                num_multiple_select=num_multiple_select,
                num_fill_blank=num_fill_blank,
                num_open=num_open,
                difficulty=difficulty,
                language=language,
                instructions=instructions,
                image_ids=list(images or {}),
            )
        )
        payload = [SystemMessage(content=system_prompt), HumanMessage(content=content)]
        if images:
            payload.append(HumanMessage(content=_figure_blocks(images)))
        model = await provision_langchain_model(
            chat_model_context(payload),
            model_id,
            "transformation",
            max_tokens=GENERATE_MAX_TOKENS,
            structured=dict(type="json"),
        )
        exam = await _invoke_structured(model, payload, parser)
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e

    questions = validate_generated_questions(exam.questions, images)
    if not questions:
        raise ExternalServiceError(
            "The model did not return any valid question. Try again, pick a "
            "different model, or check that the selected sources have content."
        )
    return exam.title.strip(), questions


async def grade_with_ai(
    question: ExamQuestion,
    student_answer: Any,
    *,
    language: Optional[str],
    model_id: Optional[str],
    images: Optional[dict[str, ChatImage]] = None,
) -> tuple[float, str]:
    """Grade an open or non-exact fill-in-the-blank answer; returns (score, feedback)."""
    try:
        parser: PydanticOutputParser[GradeOutput] = PydanticOutputParser(
            pydantic_object=GradeOutput
        )
        prompt = Prompter(prompt_template="exam/grade", parser=parser).render(  # type: ignore[arg-type]
            data=dict(
                question=question.model_dump(),
                student_answer=student_answer,
                language=language,
            )
        )
        payload: Any = prompt
        if question.image_ids:
            payload = [
                SystemMessage(content=prompt),
                HumanMessage(content=_figure_blocks(images or {}, question.image_ids)),
            ]
        model = await provision_langchain_model(
            chat_model_context(payload) if isinstance(payload, list) else prompt,
            model_id,
            "transformation",
            max_tokens=GRADE_MAX_TOKENS,
            structured=dict(type="json"),
        )
        grade = await _invoke_structured(model, payload, parser)
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e

    score = min(max(float(grade.score), 0.0), question.points)
    return score, grade.feedback.strip()
