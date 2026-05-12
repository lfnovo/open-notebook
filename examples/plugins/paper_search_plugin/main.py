from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

API_KEY = os.getenv("PAPER_PLUGIN_API_KEY", "dev-paper-key")

app = FastAPI(title="Lumina Paper Search Plugin Example")

JOBS: dict[str, dict[str, Any]] = {}

PAPERS = [
    {
        "external_id": "paper:graph-rag-2026",
        "title": "Graph Retrieval for Research Agents",
        "summary": "A mock paper about graph retrieval and agentic research workflows.",
        "url": "https://example.org/papers/graph-rag-2026",
        "authors": ["Ada Lovelace", "Grace Hopper"],
        "published_at": "2026-01-15",
        "metadata": {"venue": "LuminaConf"},
    },
    {
        "external_id": "paper:kg-teams-2025",
        "title": "Team Knowledge Graphs at Notebook Scale",
        "summary": "A mock paper about team-scoped knowledge graphs.",
        "url": "https://example.org/papers/kg-teams-2025",
        "authors": ["Katherine Johnson"],
        "published_at": "2025-11-09",
        "metadata": {"venue": "Notebook Systems"},
    },
]


class SearchRequest(BaseModel):
    source_key: str
    query: str
    limit: int = Field(10, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)


class FetchRequest(BaseModel):
    source_key: str
    external_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateRequest(BaseModel):
    source_key: str
    prompt: str
    input_text: str | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)
    output_kind: str = "markdown"
    options: dict[str, Any] = Field(default_factory=dict)


def require_auth(authorization: str | None) -> None:
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail={"error": {"code": "invalid_api_key", "message": "Invalid API key"}})


@app.get("/.well-known/lumina-plugin.json")
async def manifest():
    return {
        "schema_version": "lumina-plugin-v1",
        "name": "Paper Search",
        "provider": "Example Labs",
        "version": "1.0.0",
        "capabilities": ["search", "fetch", "output"],
        "sources": [
            {
                "key": "paper_search",
                "name": "Paper Search",
                "description": "Search and fetch mock papers.",
                "capabilities": ["search", "fetch", "output"],
            }
        ],
    }


@app.get("/lumina/v1/health")
async def health(authorization: str | None = Header(default=None)):
    require_auth(authorization)
    return {"status": "ok"}


@app.post("/lumina/v1/sources/search")
async def search(
    request: SearchRequest,
    authorization: str | None = Header(default=None),
    x_lumina_request_id: str | None = Header(default=None),
):
    require_auth(authorization)
    query = request.query.lower()
    items = [
        paper
        for paper in PAPERS
        if query in paper["title"].lower() or query in paper["summary"].lower()
    ][: request.limit]
    return {"status": "completed", "data": {"items": items}, "request_id": x_lumina_request_id}


@app.post("/lumina/v1/sources/fetch")
async def fetch(request: FetchRequest, authorization: str | None = Header(default=None)):
    require_auth(authorization)
    for paper in PAPERS:
        if paper["external_id"] == request.external_id:
            return {
                "status": "completed",
                "data": {
                    **paper,
                    "content_markdown": f"# {paper['title']}\n\n{paper['summary']}\n\nThis is full mock content.",
                    "metadata": {**paper.get("metadata", {}), "pdf_url": f"{paper['url']}.pdf"},
                },
            }
    raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "Paper not found"}})


@app.post("/lumina/v1/outputs/generate")
async def generate(request: GenerateRequest, authorization: str | None = Header(default=None)):
    require_auth(authorization)
    if request.options.get("async"):
        job_id = f"job_{uuid4().hex[:8]}"
        JOBS[job_id] = {
            "status": "completed",
            "external_job_id": job_id,
            "data": {
                "kind": request.output_kind,
                "title": "Mock Paper Output",
                "content": f"## Generated Output\n\nPrompt: {request.prompt}\n\nItems: {len(request.items)}",
                "metadata": {"mode": "async"},
            },
        }
        return {"status": "accepted", "external_job_id": job_id, "next_poll_after_seconds": 1}
    return {
        "status": "completed",
        "data": {
            "kind": request.output_kind,
            "title": "Mock Paper Output",
            "content": f"## Generated Output\n\nPrompt: {request.prompt}\n\nItems: {len(request.items)}",
            "metadata": {"mode": "sync"},
        },
    }


@app.get("/lumina/v1/jobs/{external_job_id}")
async def get_job(external_job_id: str, authorization: str | None = Header(default=None)):
    require_auth(authorization)
    job = JOBS.get(external_job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "Job not found"}})
    return job
