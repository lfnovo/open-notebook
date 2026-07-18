import operator
import os
from typing import Any, Dict, List, Optional

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

# Preferred languages for YouTube transcript selection. content-core's own
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
        if settings.default_content_processing_engine_url:
            config_kwargs["url_engine"] = settings.default_content_processing_engine_url
        if settings.default_content_processing_engine_doc:
            config_kwargs["document_engine"] = (
                settings.default_content_processing_engine_doc
            )
        if settings.docling_ocr is not None:
            config_kwargs["docling_ocr"] = settings.docling_ocr
    except Exception as e:
        # Keep the server-side traceback for diagnosing DB/deserialization
        # failures while still falling back to defaults (non-fatal).
        logger.opt(exception=True).warning(
            f"Failed to load content settings, using defaults: {e}"
        )

    try:
        model_manager = ModelManager()
        defaults = await model_manager.get_defaults()

        # Speech-to-text model config (for audio/video transcription)
        if defaults.default_speech_to_text_model:
            stt_model = await Model.get(defaults.default_speech_to_text_model)
            if stt_model:
                config_kwargs["audio_provider"] = stt_model.provider
                config_kwargs["audio_model"] = stt_model.name
                if (
                    stt_model.credential
                    and "audio_config" in ContentCoreConfig.model_fields
                ):
                    cred = await stt_model.get_credential_obj()
                    if cred:
                        config_kwargs["audio_config"] = cred.to_esperanto_config()
                logger.debug(
                    f"Using speech-to-text model: {stt_model.provider}/{stt_model.name}"
                )

        # Vision model config (for image, video frame, and PDF page analysis)
        vision_model_id = defaults.default_vision_model or defaults.default_chat_model
        if vision_model_id:
            vision_db_model = await Model.get(vision_model_id)
            if vision_db_model:
                content_state["vision_provider"] = vision_db_model.provider
                content_state["vision_model"] = vision_db_model.name
                if vision_db_model.credential:
                    cred = await vision_db_model.get_credential_obj()
                    if cred:
                        content_state["vision_config"] = cred.to_esperanto_config()
                logger.debug(
                    f"Using vision model: {vision_db_model.provider}/{vision_db_model.name}"
                )
    except Exception as e:
        logger.warning(f"Failed to retrieve model configuration: {e}")
        # Continue without custom models (content-core will use its defaults)

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
        f"docling_ocr={config_kwargs.get('docling_ocr', 'auto')})"
    )

    processed = await extract_content(
        url=content_state.get("url"),
        file_path=content_state.get("file_path"),
        content=content_state.get("content"),
        config=config,
    )

    # content-core signals a soft extraction failure (e.g. an unreachable or
    # invalid URL, via the bs4 fallback) by returning title="Error" and content
    # prefixed with "Failed to extract content:" instead of raising. Detect that
    # sentinel and raise so the job is marked failed and the source becomes
    # retryable, rather than being saved as a "completed" source whose body is
    # the error string.
    if processed.title == "Error" and (processed.content or "").startswith(
        "Failed to extract content:"
    ):
        raise ValueError(
            "Could not extract content from this source. "
            "The URL or file may be unreachable, invalid, or in an unsupported format."
        )

    # For PDFs processed by the vision pipeline, also pull literal text via
    # pdfplumber (content-core's existing extractor) and use that as the
    # primary `content`. Vision sampling skips pages by design — fine for
    # figure/layout understanding but bad for RAG/chat, since embeddings
    # built from a sampled summary can't cite content from pages that
    # were never read. We move the vision output to metadata.visual_analysis
    # so save_source can attach it as a separate insight.
    pdf_path = (
        content_state.get("file_path") if isinstance(content_state, dict) else None
    )
    if (
        processed.identified_type == "application/pdf"
        and config_kwargs.get("vision_provider")
        and pdf_path
        and os.path.exists(pdf_path)
    ):
        try:
            from content_core.processors.document.pdf import _extract_text_from_pdf

            raw_text = ((await _extract_text_from_pdf(pdf_path)) or "").strip()
            if len(raw_text) >= 200:
                processed.metadata = dict(processed.metadata or {})
                processed.metadata["visual_analysis"] = processed.content
                processed.content = raw_text
                logger.info(
                    f"PDF: using {len(raw_text)} chars of pdfplumber text as primary "
                    "content; vision output preserved as visual_analysis insight"
                )
        except Exception as e:
            logger.warning(
                f"Raw-text extraction fallback failed; keeping vision-only content: {e}"
            )

    if not processed.content or not processed.content.strip():
        url = content_state.get("url") or ""
        if url and ("youtube.com" in url or "youtu.be" in url):
            raise ValueError(
                "Could not extract content from this YouTube video. "
                "No transcript or subtitles are available. "
                "Try configuring a Speech-to-Text model in Settings "
                "to transcribe the audio instead."
            )
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

    # When extract_content ran both raw text (for full_text) AND vision-based
    # visual analysis as enrichment (figures/tables/layout), persist the
    # visual analysis as a separate insight. Keeps full_text literal so RAG
    # and chat can cite real document passages, while the visual summary
    # stays accessible to the user via the Insights tab.
    visual_analysis = (extraction.metadata or {}).get("visual_analysis")
    if visual_analysis:
        try:
            await source.add_insight("Visual analysis", visual_analysis)
        except Exception as e:
            logger.warning(
                f"Failed to attach visual analysis insight for source {source.id}: {e}"
            )

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
    if not content:
        return None
    transformation: Transformation = state["transformation"]

    logger.debug(f"Applying transformation {transformation.name}")
    # LangGraph accepts a partial state dict at runtime, but its typed
    # overloads require the full state type (langgraph typing limitation).
    result = await transform_graph.ainvoke(  # type: ignore[call-overload]
        dict(input_text=content, transformation=transformation)
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
