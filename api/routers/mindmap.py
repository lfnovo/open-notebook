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


async def _generate_from_text(text: str, model_name: str, temperature: float) -> Dict[str, Any]:
    """Generate mind map directly from already-extracted text (no OCR needed)."""
    from langchain_ollama import ChatOllama
    from open_notebook.graphs.mind_map import IntelligenceLLMService, TextProcessor
    logger.info("Starting text-based mind map generation")


    llm = ChatOllama(model=model_name, temperature=temperature)
    text_processor = TextProcessor()
    llm_service = IntelligenceLLMService(llm)
      logger.info(f"Original text length: {len(text)}")

    clean_text = await text_processor.clean_ocr_text(text)
    main_person = await text_processor.detect_main_person_async(clean_text) or "Main Subject"

    chunk_size = 10000
    chunks = [clean_text[i: i + chunk_size] for i in range(0, len(clean_text), chunk_size)]

    all_facts: list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(llm_service.extract_facts_sync, chunks))
    for result in results:
        if isinstance(result, list):
            all_facts.extend(result)

    facts = text_processor.deduplicate_facts(all_facts)
    if not facts:
        raise ValueError("No facts could be extracted from the source content")

    return await llm_service.generate_mind_map_async(main_person, facts)
     logger.success("Mind map generation completed successfully")

    return mind_map


async def _generate_from_file(file_path: str, model_name: str, temperature: float) -> Dict[str, Any]:
    """Generate mind map via OCR pipeline for uploaded files without extracted text."""
    import asyncio
    from langchain_ollama import ChatOllama
    from open_notebook.graphs.mind_map import (
        EasyOCRService,
        IntelligenceLLMService,
        MindMapPipeline,
        TextProcessor,
    )

    def build_pipeline():
        llm = ChatOllama(model=model_name, temperature=temperature)
        ocr_service = EasyOCRService(langs=["en"], max_threads=4)
        text_processor = TextProcessor()
        llm_service = IntelligenceLLMService(llm)
        return MindMapPipeline(ocr_service, text_processor, llm_service)

    pipeline = await asyncio.to_thread(build_pipeline)
    return await pipeline.generate_from_file(file_path)


@router.post("/sources/{source_id}/mindmap", response_model=MindMapResponse)
async def generate_mind_map(source_id: str, request: MindMapRequest):
    """Generate a mind map from a source's content."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        if source.full_text and source.full_text.strip():
            logger.info(f"Generating mind map from text for source {source_id}")
            mind_map = await _generate_from_text(
                source.full_text, request.model_name, request.temperature
            )
        elif source.asset and source.asset.file_path:
            logger.info(f"Generating mind map via OCR for source {source_id}")
            mind_map = await _generate_from_file(
                source.asset.file_path, request.model_name, request.temperature
            )
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
