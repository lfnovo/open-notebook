import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from open_notebook.domain.notebook import Source

router = APIRouter()

OLLAMA_BASE_URL_DEFAULT = "http://host.docker.internal:11434"

_pipeline: Optional[Any] = None


def _build_pipeline():
    from langchain_ollama import ChatOllama
    from open_notebook.graphs.infographic import (
        DossierHtmlRenderer,
        InfographicLLMService,
        InfographicPipeline,
        InfographicTextProcessor,
        TextExtractorService,
    )

    ollama_url = os.environ.get("OLLAMA_BASE_URL", OLLAMA_BASE_URL_DEFAULT)
    logger.info(f"Building InfographicPipeline — Ollama: {ollama_url}")

    llm = ChatOllama(model="qwen3", temperature=0.3, base_url=ollama_url)
    pipeline = InfographicPipeline(
        extractor=TextExtractorService(),
        processor=InfographicTextProcessor(),
        llm_service=InfographicLLMService(llm),
        renderer=DossierHtmlRenderer(),
    )
    logger.info("InfographicPipeline ready")
    return pipeline


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = _build_pipeline()
    return _pipeline


class InfographicRequest(BaseModel):
    model_name: str = "qwen3"
    temperature: float = 0.3


class InfographicResponse(BaseModel):
    html: str
    source_id: str


@router.post("/sources/{source_id:path}/infographic", response_model=InfographicResponse)
async def generate_infographic(source_id: str, request: InfographicRequest):
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not source.full_text or not source.full_text.strip():
            raise HTTPException(status_code=400, detail="Source has no text content")

        pipeline = get_pipeline()
        logger.info(f"Generating infographic for source_id={source_id}")
        result = await pipeline.generate_from_source_id(source_id)
        logger.success(f"Infographic generation completed for source_id={source_id}")

        return InfographicResponse(
            html=result.get("html", ""),
            source_id=source_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Infographic generation failed for source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Infographic generation failed: {str(e)}")
