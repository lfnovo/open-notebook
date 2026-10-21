import operator
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import content_core as cc
from content_core import ContentCoreConfig, extract_content
from content_core.common import ExtractionOutput
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from loguru import logger
from typing_extensions import Annotated, TypedDict

from open_notebook.ai.models import Model, ModelManager
from open_notebook.domain.content_settings import ContentSettings
from open_notebook.domain.notebook import Asset, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.graphs.transformation import graph as transform_graph
from open_notebook.utils.runtime_capabilities import engine_runtime_missing

# content-core >= 2.1 disables its own Loguru logging for library consumers.
# Both the API and the worker import this module before extracting anything,
# so re-enable it here to keep extraction logs in their output.
logger.enable("content_core")

# Default preferred languages for YouTube transcript selection, used when
# ContentSettings.youtube_preferred_languages is unset. content-core's own
# default is only ["en", "es", "pt"]; we keep the broader list Open Notebook has
# always intended so non-English videos still resolve a transcript.
YOUTUBE_PREFERRED_LANGUAGES = [
    "en",
    "pt",
    "es",
    "de",
    "nl",
    "en-GB",
    "fr",
    "hi",
    "ja",
    "zh-CN",
    "zh-TW",
]


class SourceState(TypedDict):
    # Input describing what to extract: url / file_path / content / delete_source.
    content_state: Dict[str, Any]
    # Result of content-core extraction (does NOT echo url/file_path back).
    extraction: ExtractionOutput
    apply_transformations: List[Transformation]
    source_id: str
    notebook_ids: List[str]
    source: Source
    transformation: Annotated[list, operator.add]
    embed: bool


class TransformationState(TypedDict):
    source: Source
    transformation: Transformation


def _usable_engine(engine: str, kind: str) -> str:
    """Return ``engine``, or "auto" when its opt-in runtime is not installed.

    The engine choice is persisted in the database; runtime availability comes
    from environment flags that are re-evaluated on every boot. A redeploy that
    drops OPEN_NOTEBOOK_ENABLE_CRAWL4AI/_DOCLING (or a failed on-demand install)
    therefore leaves a stored selection pointing at an absent runtime, and
    passing it through fails every extraction with no usable diagnostic. Falling
    back to content-core's "auto" chain keeps ingestion working, loudly.
    """
    missing_env_var = engine_runtime_missing(engine)
    if missing_env_var is None:
        return engine
    logger.warning(
        f"Configured {kind} engine '{engine}' is selected in Content Settings but "
        f"its runtime is not available in this container; falling back to 'auto'. "
        f"Set {missing_env_var}=true to enable it (see ADR-007)."
    )
    return "auto"


def _is_youtube_url(url: str) -> bool:
    """Whether ``url`` points at YouTube (by hostname, not substring)."""
    host = (urlparse(url).hostname or "").lower()
    return host in ("youtube.com", "youtu.be") or host.endswith(".youtube.com")


_YOUTUBE_NO_TRANSCRIPT_MESSAGE = (
    "Could not extract content from this YouTube video. "
    "No transcript or subtitles are available. "
    "Try configuring a Speech-to-Text model in Settings "
    "to transcribe the audio instead."
)


def _extraction_error(error: "cc.ContentCoreError", url: str) -> ValueError:
    """Turn a content-core extraction error into a user-facing permanent failure.

    content-core >= 2.2 raises typed errors instead of returning empty content.
    They are all treated as permanent (ValueError is in process_source's
    stop_on): content-core already retries transient failures internally,
    including NetworkError, and our worker's 15 attempts exist for SurrealDB
    transaction conflicts, not for re-fetching an unreachable page. A failed
    source can still be retried from the UI.

    The message is fixed per type: content-core's own text can carry proxy
    credentials, local paths or configuration details, so it only goes to the
    worker log (logged by the caller, and kept as the exception's cause).
    """

    if isinstance(error, cc.NoTranscriptFound):
        return ValueError(_YOUTUBE_NO_TRANSCRIPT_MESSAGE)
    # content-core reports a failure of both YouTube transcript paths (e.g.
    # IpBlocked) as "YouTube transcript extraction failed ..."; other
    # ExternalServiceErrors on a YouTube URL (speech-to-text provider, fetch
    # engine) get the generic message below.
    if (
        isinstance(error, cc.ExternalServiceError)
        and url
        and _is_youtube_url(url)
        and "youtube transcript" in str(error).lower()
    ):
        return ValueError(
            "YouTube blocked or failed the transcript request. If this keeps "
            "happening, set CCORE_YOUTUBE_PROXY (a residential proxy) or "
            "CCORE_YOUTUBE_COOKIES_FILE for the worker."
        )
    if isinstance(error, cc.NotFoundError):
        return ValueError(
            "The page was not found (it may have been removed or moved). Check the URL."
        )
    if isinstance(error, cc.NetworkError):
        return ValueError(
            "Could not reach this address (connection, timeout or DNS error). "
            "Check the URL and try again."
        )
    if isinstance(error, cc.InvalidInputError):
        return ValueError("This URL or input is not valid.")
    if isinstance(error, cc.UnsupportedTypeException):
        return ValueError("This file type is not supported.")
    if isinstance(error, cc.FileOperationError):
        return ValueError(
            "The file could not be read. It may be corrupted or in an "
            "unsupported format."
        )
    if isinstance(error, cc.ConfigurationError):
        return ValueError(
            "Content extraction is not configured correctly. Check the content "
            "processing engine and speech-to-text settings; the worker log has "
            "the details."
        )
    if isinstance(error, cc.ExternalServiceError):
        return ValueError("The content extraction service failed.")
    return ValueError("Could not extract content from this source.")


async def content_process(state: SourceState) -> dict:
    content_state: Dict[str, Any] = state["content_state"]

    # content-core 2.x takes engine/model overrides via ContentCoreConfig
    # (keyword-only), not inside the input dict.
    config_kwargs: Dict[str, Any] = {
        "youtube_languages": YOUTUBE_PREFERRED_LANGUAGES,
    }

    # Honor the persisted content-processing engine choices. content-core
    # accepts "auto"/"simple"/"firecrawl"/"jina"/"crawl4ai" for URLs and
    # "auto"/"docling"/"simple" for documents; falling back to "auto" keeps the
    # previous behavior when settings are unset.
    try:
        settings: ContentSettings = await ContentSettings.get_instance()  # type: ignore[assignment]
        if settings.youtube_preferred_languages:
            config_kwargs["youtube_languages"] = settings.youtube_preferred_languages
        if settings.default_content_processing_engine_url:
            config_kwargs["url_engine"] = _usable_engine(
                settings.default_content_processing_engine_url, "url"
            )
        if settings.default_content_processing_engine_doc:
            config_kwargs["document_engine"] = _usable_engine(
                settings.default_content_processing_engine_doc, "document"
            )
        if settings.docling_ocr is not None:
            config_kwargs["docling_ocr"] = settings.docling_ocr
        if settings.docling_formulas is not None:
            config_kwargs["docling_formulas"] = settings.docling_formulas
        if settings.docling_vision is not None:
            config_kwargs["docling_vision"] = settings.docling_vision
    except Exception as e:
        # Keep the server-side traceback for diagnosing DB/deserialization
        # failures while still falling back to defaults (non-fatal).
        logger.opt(exception=True).warning(
            f"Failed to load content settings, using defaults: {e}"
        )

    try:
        model_manager = ModelManager()
        defaults = await model_manager.get_defaults()
        if defaults.default_speech_to_text_model:
            stt_model = await Model.get(defaults.default_speech_to_text_model)
            if stt_model:
                config_kwargs["audio_provider"] = stt_model.provider
                config_kwargs["audio_model"] = stt_model.name
                logger.debug(
                    f"Using speech-to-text model: {stt_model.provider}/{stt_model.name}"
                )
    except Exception as e:
        logger.warning(f"Failed to retrieve speech-to-text model configuration: {e}")
        # Continue without custom audio model (content-core will use its default)

    config = ContentCoreConfig(**config_kwargs) if config_kwargs else None

    # Log the effective extraction engines so operators can confirm which engine
    # actually ran (content-core logs its own dispatch only at DEBUG). Absent
    # overrides fall back to content-core's "auto".
    if content_state.get("url"):
        target = "url"
    elif content_state.get("file_path"):
        target = "document"
    else:
        target = "content"
    logger.info(
        f"Extracting {target} via content-core "
        f"(url_engine={config_kwargs.get('url_engine', 'auto')}, "
        f"document_engine={config_kwargs.get('document_engine', 'auto')}, "
        f"docling_ocr={config_kwargs.get('docling_ocr', 'auto')}, "
        f"docling_formulas={config_kwargs.get('docling_formulas', 'auto')}, "
        f"docling_vision={config_kwargs.get('docling_vision', 'auto')})"
    )

    url = content_state.get("url") or ""
    try:
        processed = await extract_content(
            url=content_state.get("url"),
            file_path=content_state.get("file_path"),
            content=content_state.get("content"),
            config=config,
        )
    except cc.ContentCoreError as e:
        logger.warning(f"content-core extraction failed ({type(e).__name__}): {e}")
        raise _extraction_error(e, url) from e

    # Since content-core 2.2, empty content means the source was genuinely
    # empty; extraction failures raise (handled above).
    if not processed.content or not processed.content.strip():
        if url and _is_youtube_url(url):
            raise ValueError(_YOUTUBE_NO_TRANSCRIPT_MESSAGE)
        raise ValueError(
            "Could not extract any text content from this source. "
            "The content may be empty, inaccessible, or in an unsupported format."
        )

    # content-core 2.x no longer deletes the uploaded source file after
    # extraction (the delete_source flag it used to honor is gone). Preserve the
    # previous auto-delete behavior on our side.
    if content_state.get("delete_source") and content_state.get("file_path"):
        file_path = content_state["file_path"]
        try:
            os.unlink(file_path)
        except FileNotFoundError:
            logger.warning(f"File not found while trying to delete: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete source file {file_path}: {e}")

    return {"extraction": processed}


async def save_source(state: SourceState) -> dict:
    content_state = state["content_state"]
    extraction = state["extraction"]

    # Get existing source using the provided source_id
    source = await Source.get(state["source_id"])
    if not source:
        raise ValueError(f"Source with ID {state['source_id']} not found")

    # Update the source with processed content. content-core's ExtractionOutput
    # does not echo url/file_path back, so carry them from the input state.
    source.asset = Asset(
        url=content_state.get("url"), file_path=content_state.get("file_path")
    )
    source.full_text = extraction.content

    # Preserve user-set title; only overwrite placeholder or empty titles
    if extraction.title and (not source.title or source.title == "Processing..."):
        source.title = extraction.title

    await source.save()

    # NOTE: Notebook associations are created by the API immediately for UI responsiveness
    # No need to create them here to avoid duplicate edges

    if state["embed"]:
        if source.full_text and source.full_text.strip():
            logger.debug("Embedding content for vector search")
            await source.vectorize()
        else:
            logger.warning(
                f"Source {source.id} has no text content to embed, skipping vectorization"
            )

    return {"source": source}


def trigger_transformations(state: SourceState, config: RunnableConfig) -> List[Send]:
    if len(state["apply_transformations"]) == 0:
        return []

    to_apply = state["apply_transformations"]
    logger.debug(f"Applying transformations {to_apply}")

    return [
        Send(
            "transform_content",
            {
                "source": state["source"],
                "transformation": t,
            },
        )
        for t in to_apply
    ]


async def transform_content(state: TransformationState) -> Optional[dict]:
    source = state["source"]
    content = source.full_text
    # Whitespace-only text would hit the transformation graph's empty-content
    # guard; skip it here like empty text.
    if not content or not content.strip():
        return None
    transformation: Transformation = state["transformation"]

    logger.debug(f"Applying transformation {transformation.name}")
    # LangGraph accepts a partial state dict at runtime, but its typed
    # overloads require the full state type (langgraph typing limitation).
    result = await transform_graph.ainvoke(  # type: ignore[call-overload]
        dict(input_text=content, transformation=transformation),
        config=RunnableConfig(configurable={"model_id": transformation.model_id}),
    )
    await source.add_insight(transformation.title, result["output"])
    return {
        "transformation": [
            {
                "output": result["output"],
                "transformation_name": transformation.name,
            }
        ]
    }


# Create and compile the workflow
workflow = StateGraph(SourceState)

# Add nodes
workflow.add_node("content_process", content_process)
workflow.add_node("save_source", save_source)
workflow.add_node("transform_content", transform_content)
# Define the graph edges
workflow.add_edge(START, "content_process")
workflow.add_edge("content_process", "save_source")
workflow.add_conditional_edges(
    "save_source", trigger_transformations, ["transform_content"]
)
workflow.add_edge("transform_content", END)

# Compile the graph
source_graph = workflow.compile()
