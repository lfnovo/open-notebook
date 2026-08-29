import json
import time
from typing import Optional, Type, Union

from ai_prompter import Prompter
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from loguru import logger
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.database.repository import ensure_record_id
from open_notebook.domain.notebook import Notebook
from open_notebook.study.models import FlashcardList, QuizList, StudySet
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.model_utils import full_model_dump
from open_notebook.utils.text_utils import extract_text_content


class StudySetGenerationInput(CommandInput):
    notebook_id: str
    name: str
    item_count: int = 10
    model_id: Optional[str] = None


class StudySetGenerationOutput(CommandOutput):
    success: bool
    study_set_id: Optional[str] = None
    item_count: int = 0
    error_message: Optional[str] = None


async def _generate_study_set(
    input_data: StudySetGenerationInput,
    *,
    kind: str,
    prompt_template: str,
    parser_model: Type[Union[FlashcardList, QuizList]],
) -> StudySetGenerationOutput:
    """Shared flashcards/quiz generation flow.

    Follows the transformation.py pattern (Prompter + PydanticOutputParser
    for structured output) and the podcast_commands.py pattern for saving a
    record linked to the async job (`command=ensure_record_id(...)`).
    """
    start_time = time.time()

    try:
        logger.info(f"Starting {kind} generation for notebook: {input_data.notebook_id}")

        notebook = await Notebook.get(input_data.notebook_id)
        if not notebook:
            raise ValueError(f"Notebook '{input_data.notebook_id}' not found")

        # Notebook.get_context() builds the long-form (full_text + insights)
        # context meant for podcast/LLM generation workflows - same call
        # PodcastService.submit_generation_job() falls back to for
        # notebook-sourced content. build_notebook_context(notebook, None)
        # was used previously, but with no context_config it defaults every
        # source to context_size="short", which omits full_text entirely
        # (id/title/insights only) - so notebooks without pre-generated
        # insights produced near-empty content that the model, following its
        # own "thin content -> return fewer items" instruction, correctly
        # reduced to zero flashcards/quiz items.
        content = await notebook.get_context()
        if not content or not content.strip():
            raise ValueError(
                f"Notebook '{notebook.name}' has no source/note content to generate "
                f"{kind} from. Add sources or notes to the notebook first."
            )

        parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=parser_model)
        system_prompt = Prompter(prompt_template=prompt_template, parser=parser).render(  # type: ignore[arg-type]
            data={"content": content, "item_count": input_data.item_count}
        )

        # default_type="transformation" both selects the model (transformation
        # default, falling back to the chat default) and is the task_type
        # recorded by the usage-tracking callback in provision_langchain_model()
        # - see open_notebook/ai/provision.py.
        chain = await provision_langchain_model(
            system_prompt,
            input_data.model_id,
            "transformation",
            max_tokens=8192,
        )

        response = await chain.ainvoke(system_prompt)
        response_content = extract_text_content(response.content)
        cleaned_content = clean_thinking_content(response_content)

        try:
            parsed = parser.parse(cleaned_content)
        except Exception as parse_error:
            # Observed with nvidia/nemotron-3-super-120b-a12b:free on quiz
            # generation: the model returns perfectly well-formed items but
            # as a bare JSON array `[{...}, ...]` instead of the wrapped
            # `{"items": [...]}` object PydanticOutputParser expects
            # (intermittent format-following slip, not a systemic "can't do
            # structured output" failure - flashcards succeeded with the
            # same model in the same run). Detect exactly that shape and
            # wrap it before validating; anything else (truncated JSON,
            # prose, a dict missing "items", etc.) is a genuine malformed
            # response and must still raise via the original parse_error.
            try:
                raw = json.loads(cleaned_content)
            except (json.JSONDecodeError, TypeError):
                raw = None
            if not isinstance(raw, list):
                raise parse_error
            logger.warning(
                f"{kind.capitalize()} model returned a bare JSON array "
                'instead of {"items": [...]}; wrapping it before validation'
            )
            parsed = parser_model.model_validate({"items": raw})

        if not parsed.items:
            raise ValueError(
                f"The model did not return any {kind} items. Try again or use a "
                "different model."
            )

        study_set = StudySet(
            notebook=str(notebook.id),
            kind=kind,
            name=input_data.name,
            content=content,
            items=[full_model_dump(item) for item in parsed.items],
            model_id=input_data.model_id,
            command=ensure_record_id(input_data.execution_context.command_id)
            if input_data.execution_context
            else None,
        )
        await study_set.save()

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully generated {kind} study set: {study_set.id} "
            f"({len(parsed.items)} items) in {processing_time:.2f}s"
        )

        return StudySetGenerationOutput(
            success=True,
            study_set_id=str(study_set.id),
            item_count=len(parsed.items),
        )

    except ValueError:
        raise

    except Exception as e:
        logger.error(f"{kind.capitalize()} generation failed: {e}")
        logger.exception(e)
        raise RuntimeError(str(e)) from e


@command("generate_flashcards", app="open_notebook", retry={"max_attempts": 1})
async def generate_flashcards_command(
    input_data: StudySetGenerationInput,
) -> StudySetGenerationOutput:
    """Generate a flashcard study set from a notebook's context."""
    return await _generate_study_set(
        input_data,
        kind="flashcards",
        prompt_template="study/flashcards",
        parser_model=FlashcardList,
    )


@command("generate_quiz", app="open_notebook", retry={"max_attempts": 1})
async def generate_quiz_command(
    input_data: StudySetGenerationInput,
) -> StudySetGenerationOutput:
    """Generate a quiz study set from a notebook's context."""
    return await _generate_study_set(
        input_data,
        kind="quiz",
        prompt_template="study/quiz",
        parser_model=QuizList,
    )
