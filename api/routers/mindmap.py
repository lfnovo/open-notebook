import asyncio
import base64
import os
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import numpy as np
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from open_notebook.domain.notebook import Source

router = APIRouter()

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093")


def _decode_source_id(source_id: str) -> str:
    """URL-decode source_id — FastAPI :path doesn't auto-decode %3A → : """
    return unquote(source_id)

# Module-level orchestrator instance (initialized on first use)
_orchestrator: Optional[Any] = None


def _build_orchestrator():
    """Build and return a KafkaMindMapOrchestrator with a fully wired MindMapPipeline."""
    from langchain_ollama import ChatOllama
    from open_notebook.graphs.mind_map import (
        EasyOCRService,
        IntelligenceLLMService,
        KafkaMindMapOrchestrator,
        MindMapPipeline,
        TextProcessor,
    )

    # Read env vars fresh at build time — never at module load — so the correct
    # runtime value is always used even after container restarts or hot-reloads.
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    kafka_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093")

    logger.info(f"Building MindMapPipeline — Ollama: {ollama_url}, Kafka: {kafka_servers}")
    llm = ChatOllama(model="qwen3", temperature=0.2, base_url=ollama_url)
    ocr_service = EasyOCRService()
    text_processor = TextProcessor()
    llm_service = IntelligenceLLMService(llm)
    pipeline = MindMapPipeline(
        ocr_service=ocr_service,
        processor=text_processor,
        llm_service=llm_service,
    )
    orchestrator = KafkaMindMapOrchestrator(
        pipeline=pipeline,
        bootstrap_servers=kafka_servers,
    )
    logger.info("KafkaMindMapOrchestrator ready")
    return orchestrator


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = _build_orchestrator()
    return _orchestrator


class MindMapRequest(BaseModel):
    model_name: str = "qwen3"
    temperature: float = 0.2


class MindMapResponse(BaseModel):
    mind_map: Dict[str, Any]
    source_id: str


@router.post("/sources/{source_id}/mindmap", response_model=MindMapResponse)
async def generate_mind_map(source_id: str, request: MindMapRequest):
    """Generate a mind map from a source's content using KafkaMindMapOrchestrator."""
    try:
        source_id = _decode_source_id(source_id)
        try:
            source = await Source.get(source_id)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

        if not source.full_text or not source.full_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Source has no text content to generate a mind map from",
            )

        orchestrator = get_orchestrator()

        # Publish job to Kafka (non-blocking, best-effort)
        asyncio.create_task(_safe_produce(orchestrator, source_id))

        # Generate directly via the pipeline (no timeout)
        logger.info(f"Generating mind map for source_id={source_id}")
        mind_map = await orchestrator.pipeline.generate_from_source_id(source_id)
        logger.success(f"Mind map generation completed for source_id={source_id}")

        return MindMapResponse(mind_map=mind_map, source_id=source_id)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Mind map generation failed for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Mind map generation failed: {str(e)}")


async def _safe_produce(orchestrator, source_id: str):
    """Fire-and-forget Kafka job publish — errors are logged, never raised."""
    try:
        await orchestrator.produce_jobs([source_id])
    except Exception as e:
        logger.warning(f"Kafka produce skipped for {source_id}: {e}")


async def start_kafka_consumer():
    """Start the KafkaMindMapOrchestrator consumer as a background task."""
    try:
        orchestrator = get_orchestrator()
        logger.info("Starting KafkaMindMapOrchestrator consumer...")
        await orchestrator.start_consumer()
    except Exception as e:
        logger.warning(f"Kafka consumer could not start (Kafka may be unavailable): {e}")


class SourceImagesResponse(BaseModel):
    images: List[str]  # base64-encoded PNG strings
    source_id: str
    count: int


class NodeSummaryRequest(BaseModel):
    node_name: str
    root_subject: str  # the root node label (person/topic name)


class NodeSummaryResponse(BaseModel):
    summary: str
    node_name: str
    root_subject: str


@router.post("/sources/{source_id}/node-summary", response_model=NodeSummaryResponse)
async def get_node_summary(source_id: str, request: NodeSummaryRequest):
    """Generate a detailed summary for a specific mind map node using the source content."""
    try:
        logger.info(f"Node summary request: source_id={source_id!r}, node={request.node_name!r}")
        source_id = _decode_source_id(source_id)
        logger.info(f"Decoded source_id={source_id!r}")
        try:
            source = await Source.get(source_id)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        if not source.full_text or not source.full_text.strip():
            raise HTTPException(status_code=400, detail="Source has no text content")

        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOllama(model="qwen3", temperature=0.3, base_url=ollama_url)

        # Truncate source text to avoid context overflow (~12k chars)
        context_text = source.full_text[:12000]

        system_prompt = (
            "You are an expert analyst. Given source document content, provide a detailed, "
            "well-structured summary about a specific topic as it relates to the main subject. "
            "Be thorough, cite specific facts from the source, and organize your response clearly. "
            "Do not add information not present in the source. "
            "STRICT FORMATTING RULES: "
            "- Do NOT use any markdown headers (no #, ##, ### etc). "
            "- Do NOT use --- horizontal rules. "
            "- Use **bold** only for section titles and key terms. "
            "- Use plain numbered lists or bullet points for structure. "
            "- Write in clean plain text paragraphs."
        )

        user_prompt = (
            f"Discuss what these sources say about '{request.node_name}', "
            f"in the larger context of '{request.root_subject}'.\n\n"
            f"Source content:\n{context_text}"
        )

        def _run_llm():
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = llm.invoke(messages)
            return response.content

        summary = await asyncio.to_thread(_run_llm)

        # Strip <think>...</think> tags if model outputs chain-of-thought
        import re
        summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL).strip()
        # Strip markdown headers (###, ##, #) — replace with bold text instead
        summary = re.sub(r'^#{1,6}\s+(.+)$', r'**\1**', summary, flags=re.MULTILINE)
        # Strip horizontal rules
        summary = re.sub(r'^-{3,}$', '', summary, flags=re.MULTILINE)
        # Collapse multiple blank lines
        summary = re.sub(r'\n{3,}', '\n\n', summary).strip()

        logger.info(f"Node summary generated for '{request.node_name}' in source {source_id}")
        return NodeSummaryResponse(
            summary=summary,
            node_name=request.node_name,
            root_subject=request.root_subject,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Node summary failed for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Node summary failed: {str(e)}")


class SourceSummaryResponse(BaseModel):
    summary: str
    source_id: str


@router.post("/sources/{source_id}/summary", response_model=SourceSummaryResponse)
async def get_source_summary(source_id: str):
    """Generate a full summary of the source document using Ollama qwen3 via SummaryPipeline."""
    try:
        source_id = _decode_source_id(source_id)
        logger.info(f"Source summary request: source_id={source_id!r}")

        from langchain_ollama import ChatOllama
        from open_notebook.graphs.summary import SummaryPipeline, SummaryTextProcessor, SummaryLLMService

        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        llm = ChatOllama(model="qwen3", temperature=0.3, base_url=ollama_url)

        pipeline = SummaryPipeline(
            processor=SummaryTextProcessor(),
            llm_service=SummaryLLMService(llm),
        )

        result = await pipeline.generate_from_source_id(source_id)

        logger.info(f"Source summary generated for source {source_id}")
        return SourceSummaryResponse(summary=result["summary"], source_id=source_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Source summary failed for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Source summary failed: {str(e)}")


def _extract_images_from_pdf(file_path: str) -> List[str]:
    """
    Extract images from a PDF using two strategies:
    1. Embedded XObject images (photos embedded in the PDF stream)
    2. Page rendering — render each page as a high-res image (catches scanned PDFs,
       pages with photos drawn directly, charts, etc.)
    Returns a deduplicated list of base64-encoded PNG strings.
    """
    import io
    import fitz  # PyMuPDF
    from PIL import Image

    images_b64: List[str] = []
    seen_sizes: set = set()  # deduplicate by (width, height, first-bytes)

    doc = fitz.open(file_path)

    for page_index in range(len(doc)):
        page = doc[page_index]

        # ── Strategy 1: extract embedded XObject images ──────────────────────
        embedded = page.get_images(full=True)
        page_has_embedded = False

        for img_info in embedded:
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                img = Image.open(io.BytesIO(img_bytes))
                # Skip tiny icons / artifacts
                if img.width < 80 or img.height < 80:
                    continue
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="PNG")
                raw = buf.getvalue()
                key = (img.width, img.height, raw[:64])
                if key in seen_sizes:
                    continue
                seen_sizes.add(key)
                images_b64.append(base64.b64encode(raw).decode("utf-8"))
                page_has_embedded = True
            except Exception as e:
                logger.warning(f"Skipping embedded image xref={xref} on page {page_index}: {e}")

        # ── Strategy 2: render the full page if it has no embedded images ────
        # This catches scanned PDFs and pages where photos are drawn as page content
        if not page_has_embedded:
            try:
                # 150 DPI is a good balance of quality vs size
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Skip pages that are mostly white (text-only pages)
                arr = np.array(img)
                white_ratio = (arr > 240).all(axis=2).mean()
                if white_ratio > 0.92:
                    # Mostly blank/text page — skip
                    continue

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                raw = buf.getvalue()
                key = (img.width, img.height, raw[:64])
                if key not in seen_sizes:
                    seen_sizes.add(key)
                    images_b64.append(base64.b64encode(raw).decode("utf-8"))
            except Exception as e:
                logger.warning(f"Page render failed for page {page_index}: {e}")

    doc.close()
    return images_b64


def _extract_images_from_docx(file_path: str) -> List[str]:
    """Extract embedded images from a .docx file using python-docx."""
    import io
    from PIL import Image
    from docx import Document

    images_b64: List[str] = []
    seen: set = set()

    doc = Document(file_path)
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            try:
                img_bytes = rel.target_part.blob
                img = Image.open(io.BytesIO(img_bytes))
                if img.width < 80 or img.height < 80:
                    continue
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="PNG")
                raw = buf.getvalue()
                key = raw[:128]
                if key in seen:
                    continue
                seen.add(key)
                images_b64.append(base64.b64encode(raw).decode("utf-8"))
            except Exception as e:
                logger.warning(f"Skipping docx image: {e}")

    return images_b64


@router.get("/sources/{source_id}/images", response_model=SourceImagesResponse)
async def get_source_images(source_id: str):
    """Extract images from a source's PDF/file and return them as base64 PNGs."""
    try:
        source_id = _decode_source_id(source_id)
        try:
            source = await Source.get(source_id)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

        file_path = source.asset.file_path if source.asset else None
        if not file_path or not os.path.exists(file_path):
            # No file — return empty list gracefully
            return SourceImagesResponse(images=[], source_id=source_id, count=0)

        ext = os.path.splitext(file_path)[1].lower()
        images_b64: List[str] = []

        if ext == ".pdf":
            # Run in thread pool — CPU-bound PDF rendering
            images_b64 = await asyncio.to_thread(_extract_images_from_pdf, file_path)
        elif ext in (".docx", ".doc"):
            images_b64 = await asyncio.to_thread(_extract_images_from_docx, file_path)
        else:
            # For image files themselves, return the file directly
            try:
                import io
                from PIL import Image
                img = Image.open(file_path)
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="PNG")
                images_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
            except Exception as e:
                logger.warning(f"Could not read file as image for {source_id}: {e}")

        logger.info(f"Extracted {len(images_b64)} images from source {source_id}")
        return SourceImagesResponse(images=images_b64, source_id=source_id, count=len(images_b64))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image extraction failed for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Image extraction failed: {str(e)}")
