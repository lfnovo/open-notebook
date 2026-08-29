import time
from typing import Optional, Tuple

from ai_prompter import Prompter
from esperanto import LanguageModel
from loguru import logger
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.ai.models import ModelType, _provider_and_name, model_manager
from open_notebook.ai.pricing import get_price_per_token
from open_notebook.ai.provision import _attach_usage_tracking
from open_notebook.domain.notebook import Note, Notebook
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.context_builder import (
    build_notebook_context,
    format_source_context,
)
from open_notebook.utils.text_utils import extract_text_content
from open_notebook.utils.token_utils import token_count

# Per-invocation ceiling for this command specifically - separate from
# STUDY_BUDGET_USD (a monthly cap that only ever skips paid *fallback*
# models once trailing spend is exhausted). This command combines whatever
# sources the user picked, which could be several whole books at once, so
# it gets its own hard, single-run ceiling on top of that.
MAX_COST_PER_RUN_USD = 0.30

# Bounds the worst-case output cost in the pre-flight estimate below, and is
# passed as the real max_tokens to the model call so the estimate can't be
# invalidated by a longer-than-expected response.
MAX_OUTPUT_TOKENS = 4096


class AskAcrossSourcesInput(CommandInput):
    notebook_id: str
    question: str
    # Same shape POST /api/chat/context already accepts and
    # build_notebook_context() already consumes:
    # {"sources": {id: "full content"|"not in"}, "notes": {...}}
    context_config: dict


class AskAcrossSourcesOutput(CommandOutput):
    success: bool
    note_id: Optional[str] = None
    model_used: Optional[str] = None
    estimated_cost_usd: Optional[float] = None
    error_message: Optional[str] = None


async def _select_model_within_run_budget(
    input_tokens: int,
) -> Tuple[LanguageModel, str, str, float]:
    """Pick the first large-context-capable model whose estimated cost for
    this run stays under MAX_COST_PER_RUN_USD.

    Reuses model_manager's existing free-first, already-budget-aware
    resolution (get_default_model + get_fallback_chain already skip paid
    fallbacks once the monthly STUDY_BUDGET_USD is exhausted) and layers a
    second, per-run cost estimate on top - free candidates are always
    accepted; a paid one only if its estimated cost for this exact amount
    of content fits under the $0.30 ceiling.

    Raises ValueError if nothing fits (only possible if every configured
    large-context model, free ones included, failed to resolve).
    """
    primary = await model_manager.get_default_model("large_context")
    candidates: list[ModelType] = [primary] if primary is not None else []

    primary_provider, primary_name = (
        _provider_and_name(primary) if primary is not None else (None, None)
    )
    # Fetch fallbacks regardless of whether the primary resolved - a primary
    # that failed to resolve (deleted model, broken credential) is exactly
    # when the fallback chain matters most, not a reason to skip it.
    fallbacks = await model_manager.get_fallback_chain(
        "large_context",
        primary_provider=primary_provider,
        primary_model_name=primary_name,
    )
    candidates.extend(fallbacks)

    for candidate in candidates:
        if not isinstance(candidate, LanguageModel):
            logger.warning(
                f"Skipping non-language large_context candidate: {type(candidate).__name__}"
            )
            continue

        provider, name = _provider_and_name(candidate)
        input_price, output_price = await get_price_per_token(provider or "", name or "")
        is_paid = input_price > 0 or output_price > 0

        if not is_paid:
            return candidate, provider or "", name or "", 0.0

        estimated_cost = input_tokens * input_price + MAX_OUTPUT_TOKENS * output_price
        if estimated_cost < MAX_COST_PER_RUN_USD:
            return candidate, provider or "", name or "", estimated_cost

        logger.info(
            f"Skipping paid model {provider}/{name} for ask_across_sources: "
            f"estimated cost ${estimated_cost:.4f} would exceed the "
            f"${MAX_COST_PER_RUN_USD} per-run limit for {input_tokens} input tokens"
        )

    raise ValueError(
        "No configured model fits within the $0.30-per-use limit for this "
        "much content. Try selecting fewer or shorter sources."
    )


@command("ask_across_sources", app="open_notebook", retry={"max_attempts": 1})
async def ask_across_sources_command(
    input_data: AskAcrossSourcesInput,
) -> AskAcrossSourcesOutput:
    """Answer a question by combining several selected sources at once.

    Runs as an async background job specifically so combining large/multiple
    sources (whole books included) can never hit the synchronous chat/
    transformation timeout - the content is built the exact same way
    POST /api/chat/context does, just without an HTTP request blocked on it.
    """
    start_time = time.time()

    try:
        logger.info(
            f"Starting ask_across_sources for notebook: {input_data.notebook_id}"
        )

        notebook = await Notebook.get(input_data.notebook_id)
        if not notebook:
            raise ValueError(f"Notebook '{input_data.notebook_id}' not found")

        context_data, total_content = await build_notebook_context(
            notebook, input_data.context_config
        )
        if not total_content or not total_content.strip():
            raise ValueError(
                "None of the selected sources have usable content. Pick at "
                "least one source that has finished processing."
            )

        input_tokens = token_count(total_content)
        model, provider, model_name, estimated_cost = await _select_model_within_run_budget(
            input_tokens
        )

        system_prompt = Prompter(prompt_template="study/ask_sources").render(
            data={
                "content": format_source_context(context_data),
                "question": input_data.question,
            }
        )

        lc_model = model.to_langchain()
        lc_model = _attach_usage_tracking(lc_model, provider, model_name, "chat")

        response = await lc_model.ainvoke(system_prompt, max_tokens=MAX_OUTPUT_TOKENS)
        answer = clean_thinking_content(extract_text_content(response.content))

        if not answer.strip():
            raise ValueError("The model returned an empty answer. Try again.")

        note = Note(
            title=input_data.question[:80],
            content=answer,
            note_type="ai",
        )
        await note.save()
        await note.add_to_notebook(input_data.notebook_id)

        processing_time = time.time() - start_time
        logger.info(
            f"ask_across_sources completed: note {note.id}, model {provider}/{model_name}, "
            f"~${estimated_cost:.4f}, {processing_time:.2f}s"
        )

        return AskAcrossSourcesOutput(
            success=True,
            note_id=str(note.id),
            model_used=f"{provider}/{model_name}",
            estimated_cost_usd=estimated_cost,
        )

    except ValueError:
        raise

    except Exception as e:
        logger.error(f"ask_across_sources failed: {e}")
        logger.exception(e)
        raise RuntimeError(str(e)) from e
