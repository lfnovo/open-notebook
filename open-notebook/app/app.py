from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import get_settings
from ingest import ingest_file, ingest_text, ingest_youtube
from rag import answer


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("open-notebook-prototype")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    k: int = Field(default=5, ge=1, le=20)


app = FastAPI(title="Open Notebook Prototype")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/query")
async def query_endpoint(payload: QueryRequest) -> dict:
    logger.info("query received: k=%s", payload.k)
    return answer(payload.query, k=payload.k, settings=get_settings())


@app.post("/ingest")
async def ingest_endpoint(request: Request, file: UploadFile | None = File(default=None)) -> dict:
    content_type = request.headers.get("content-type", "")
    current_settings = get_settings()
    try:
        if file is not None:
            raw = await file.read()
            source_name = file.filename or "upload.txt"
            suffix = Path(source_name).suffix or ".txt"
            if suffix.lower() == ".pdf":
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(raw)
                    tmp_path = Path(tmp.name)
                try:
                    result = ingest_file(tmp_path, settings=current_settings)
                    result["source"] = source_name
                finally:
                    tmp_path.unlink(missing_ok=True)
            else:
                text = raw.decode("utf-8", errors="ignore")
                result = ingest_text(text, source_name, settings=current_settings)
            return {"status": "ok", **result}

        if "application/json" in content_type:
            body = await request.json()
            url = body.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="JSON body must include a url")
            result = ingest_youtube(url, settings=current_settings)
            return {"status": "ok", **result}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(status_code=400, detail="Provide a multipart file upload or JSON {\"url\": ...}")


@app.get("/health")
async def health() -> dict:
    current_settings = get_settings()
    return {"status": "ok", "config": json.loads(json.dumps({"vector_store": current_settings.vector_store}))}
