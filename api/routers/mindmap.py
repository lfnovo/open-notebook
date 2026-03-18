import asyncio
import concurrent.futures
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from open_notebook.domain.notebook import Source

router = APIRouter()


class MindMapRequest(BaseModel):
    model_name: str = "qwen3"
    temperature: float = 0.2


class MindMapResponse(BaseModel):
    mind_map: Dict[str, Any]
    source_id: str


def _build_pipeline(model_name: str, temperature: float):
    """Lazy import and build pipeline to avoid loading heavy deps at startup."""
    from langchain_ollama import ChatOllama

    from open_notebook.graphs.mind_map import (
        EasyOCRService,
        IntelligenceLLMService,
        MindMapPipeline,
        TextProcessor,
    )

    llm = ChatOllama(model=model_name, temperature=temperature)
    ocr_service = EasyOCRService(langs=["en"], max_threads=4)
    text_processor = TextProcessor()
    llm_service = IntelligenceLLMService(llm)
    return MindMapPipeline(ocr_service, text_processor, llm_service)


async def _generate_from_text(text: str, model_name: str, temperature: float) -> Dict[str, Any]:
    """Generate mind map directly from extracted text (no OCR needed)."""
    from langchain_ollama import ChatOllama

    from open_notebook.graphs.mind_map import (
        IntelligenceLLMService,
        MindMapPipeline,
        TextProcessor,
    )

    llm = ChatOllama(model=model_name, temperature=temperature)
    text_processor = TextProcessor()
    llm_service = IntelligenceLLMService(llm)

    # Clean text
    clean_text = await text_processor.clean_ocr_text(text)

    # Detect main person/subject
    main_person = await text_processor.detect_main_person_async(clean_text)
    main_person = main_person or "Main Subject"

    # Chunk and extract facts
    chunk_size = 10000
    chunks = [clean_text[i : i + chunk_size] for i in range(0, len(clean_text), chunk_size)]

    all_facts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(llm_service.extract_facts_sync, chunks))
    for result in results:
        if isinstance(result, list):
            all_facts.extend(result)

    facts = text_processor.deduplicate_facts(all_facts)
    if not facts:
        raise ValueError("No facts could be extracted from the source content")

    mind_map = await llm_service.generate_mind_map_async(main_person, facts)
    return mind_map


@router.post("/sources/{source_id}/mindmap", response_model=MindMapResponse)
async def generate_mind_map(source_id: str, request: MindMapRequest):
    """Generate a mind map from a source's content."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Prefer already-extracted full_text to avoid re-OCR
        if source.full_text and source.full_text.strip():
            logger.info(f"Generating mind map from text content for source {source_id}")
            mind_map = await _generate_from_text(
                source.full_text, request.model_name, request.temperature
            )
        elif source.asset and source.asset.file_path:
            # Fall back to OCR pipeline for files without extracted text
            logger.info(f"Generating mind map via OCR pipeline for source {source_id}")
            pipeline = await asyncio.to_thread(
                _build_pipeline, request.model_name, request.temperature
            )
            mind_map = await pipeline.generate_from_file(source.asset.file_path)
        else:
            raise HTTPException(
                status_code=400,
                detail="Source has no text content or file to generate a mind map from",
            )

        return MindMapResponse(mind_map=mind_map, source_id=source_id)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Mind map generation failed for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Mind map generation failed: {str(e)}")
