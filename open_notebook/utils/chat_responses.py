"""Materialize private quiz payloads into persistent, positioned chat widgets."""

import asyncio
import concurrent.futures
import re
import unicodedata
from typing import Any

from loguru import logger
from pydantic import ValidationError

from open_notebook.ai.models import model_manager
from open_notebook.domain.chat_quiz import ChatQuiz
from open_notebook.exceptions import OpenNotebookError
from open_notebook.graphs.chat_quiz import InlineQuiz, repair_inline_quiz
from open_notebook.graphs.exam import validate_generated_questions
from open_notebook.utils.chat_images import message_images
from open_notebook.utils.text_utils import extract_text_content

QUIZ_BLOCK = re.compile(
    r"```chat-quiz[ \t]*\r?\n?(.*?)```(?![a-zA-Z-])", re.DOTALL | re.IGNORECASE
)
QUIZ_START = re.compile(r"```chat-quiz\b", re.IGNORECASE)
QUIZ_UNAVAILABLE = "[[quiz-unavailable]]"


def latest_request(messages: list[Any]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", None) == "human":
            return extract_text_content(message.content)
    return ""


def requested_widgets(request: str) -> tuple[bool, bool]:
    """Detect explicit requests in the current turn, never in old conversation text."""
    text = "".join(
        c
        for c in unicodedata.normalize("NFKD", request.lower())
        if not unicodedata.combining(c)
    )
    visual = bool(
        re.search(
            r"\b(imagen(?:es)?|imange(?:n|es)|ilustracion(?:es)?|recortes?|figuras?|images?|illustrations?|crops?)\b",
            text,
        )
    )
    quiz = bool(
        re.search(
            r"\b(examen(?:es)?|examnes|tests?|quizzes?|cuestionarios?|autoevaluacion|practice questions)\b",
            text,
        )
    )
    if re.search(
        r"\b(no|sin|without|don't|do not)\s+(?:\w+\s+){0,2}(?:imagenes|imagen|images|illustrations|figuras)\b",
        text,
    ):
        visual = False
    if re.search(
        r"\b(no|sin|without|don't|do not)\s+(?:\w+\s+){0,2}(?:examen|examenes|tests?|quiz)\b",
        text,
    ):
        quiz = False
    return visual, quiz


def quiz_instructions() -> str:
    return (
        "\n\nINTERACTIVE PRACTICE IN RESPONSES:\n"
        "When the user asks for an exam, examen, cuestionario, test, quiz, practice questions or a self-check, render it "
        "as an interactive test. You may also offer a short test when applying a freshly "
        "explained concept would materially help learning; do not force a quiz into every "
        "answer or when the user wants explanation only. Place at most ONE test exactly "
        "where it belongs in your response, using a fenced block with language chat-quiz "
        "and a valid JSON object (not ordinary Markdown questions). Use the user's language. "
        "The block is converted to an interactive card; its answer key stays private until "
        "submission. Do NOT repeat correct answers, explanations or rubrics outside the block. "
        "JSON fields: title (string), language (language name), questions (1 to 5 objects). "
        "Each question has type (multiple_choice, multiple_select, fill_blank or open), "
        "prompt, points (positive number), image_ids ([] unless a real response figure is "
        "essential), explanation (answer feedback). multiple_choice: options (2-6 strings), "
        "correct_option (0-based index). multiple_select: options (3-6 strings), correct_options "
        "(at least two indexes). fill_blank: prompt has ___ for each blank, blanks (array of "
        "arrays of accepted strings). open: reference_answer and rubric. Ground questions and "
        "answers in the current material. If visual tools attached image N, reference it in "
        "a question as figureN (image_ids); never refer to an unavailable image. "
        "Questions must be answerable from their wording and attached figures. Do not use answer sheets, marked answers or solved exercises as test figures; crop out solutions. "
        "Previous [[quiz:...]] markers refer to existing tests: never copy them to create a new test."
    )


async def materialize_chat_response(
    reply: Any,
    session_id: str,
    model_id: str | None,
    request: str = "",
    context: str = "",
) -> Any:
    content = re.sub(r"\[\[quiz:[^\]]+\]\]", "", reply.content)
    matches = list(QUIZ_BLOCK.finditer(content))
    remainder = QUIZ_BLOCK.sub("", content)
    incomplete = QUIZ_START.search(remainder)
    if not matches and not incomplete:
        if not requested_widgets(request)[1]:
            return reply.model_copy(update={"content": content})
        # Ordinary Markdown exams are not an interactive response. Convert the
        # requested test before exposing prose that might contain its answer key.
        pool = {
            f"figure{i + 1}": image for i, image in enumerate(message_images(reply))
        }
        try:
            requested_quiz = await repair_inline_quiz(
                "Create the requested interactive exam using this material.\nUser request:\n"
                + request
                + "\nSource material:\n"
                + context
                + "\nDraft:\n"
                + content,
                pool,
                model_id,
            )
            content = "\n\n".join(re.findall(r"\[\[image:\d+\]\]", content))
            content += "\n\n```chat-quiz\n" + requested_quiz.model_dump_json() + "\n```"
            matches = list(QUIZ_BLOCK.finditer(content))
        except OpenNotebookError as exc:
            logger.warning(f"Requested inline exam unavailable ({type(exc).__name__})")
            figures = "\n\n".join(re.findall(r"\[\[image:\d+\]\]", content))
            return reply.model_copy(
                update={"content": (figures + "\n\n" + QUIZ_UNAVAILABLE).strip()}
            )
    # A truncated tail can contain private answer keys: never return it as prose.
    tail_start = QUIZ_START.search(content, matches[-1].end() if matches else 0)
    raw = "\n".join(match.group(1).strip() for match in matches)
    if tail_start:
        raw += "\n" + content[tail_start.end() :]
        content = content[: tail_start.start()] + QUIZ_UNAVAILABLE
    pool = {f"figure{i + 1}": image for i, image in enumerate(message_images(reply))}
    generated = None
    questions = []
    if len(matches) == 1 and not incomplete:
        try:
            generated = InlineQuiz.model_validate_json(raw)
            questions = validate_generated_questions(generated.questions, pool)
        except ValidationError:
            logger.warning("Inline quiz schema needs repair")
    needs_repair = generated is None or len(questions) != len(generated.questions)
    if needs_repair:
        try:
            repaired = await repair_inline_quiz(raw, pool, model_id)
            repaired_questions = validate_generated_questions(repaired.questions, pool)
            if repaired_questions:
                generated, questions = repaired, repaired_questions
        except OpenNotebookError as exc:
            logger.warning(f"Inline quiz repair unavailable ({type(exc).__name__})")
    if not questions or generated is None:
        # Preserve the explanation and real figures, without exposing raw test JSON.
        logger.warning("Inline quiz omitted; preserving the chat explanation")
        content = QUIZ_BLOCK.sub(QUIZ_UNAVAILABLE, content)
        if QUIZ_UNAVAILABLE not in content:
            content += "\n\n" + QUIZ_UNAVAILABLE
        return reply.model_copy(update={"content": content.strip()})
    used = {key for question in questions for key in question.image_ids}
    if not model_id:
        model_id = (await model_manager.get_defaults()).default_chat_model
    quiz = ChatQuiz(
        session_id=session_id,
        title=generated.title.strip() or "Quiz",
        language=generated.language,
        model_id=model_id,
        questions=[question.model_dump() for question in questions],
        images={key: image for key, image in pool.items() if key in used},
    )
    await quiz.save()
    marker = f"[[quiz:{quiz.id}]]"
    placed = False

    def place_quiz(_: re.Match[str]) -> str:
        nonlocal placed
        if placed:
            return ""
        placed = True
        return f"\n\n{marker}\n\n"

    content = QUIZ_BLOCK.sub(place_quiz, content)
    content = content.replace(QUIZ_UNAVAILABLE, "" if placed else marker).strip()
    return reply.model_copy(
        update={
            "content": content,
            "additional_kwargs": {
                **reply.additional_kwargs,
                "response_quizzes": [quiz.id],
            },
        }
    )


def run_chat_response(
    reply: Any,
    session_id: str,
    model_id: str | None,
    request: str = "",
    context: str = "",
) -> Any:
    """Bridge only the two legacy synchronous SQLite chat nodes."""

    def run():
        return asyncio.run(
            materialize_chat_response(reply, session_id, model_id, request, context)
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return run()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return executor.submit(run).result()
