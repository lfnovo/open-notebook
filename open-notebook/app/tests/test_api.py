from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["EMBEDDING_MODEL"] = "hash"
os.environ["MODEL_PROVIDER"] = "local"

from app import app


client = TestClient(app)


def test_ingest_then_query_roundtrip(tmp_path: Path) -> None:
    os.environ["DATA_DIR"] = str(tmp_path / "data")
    os.environ["INDEX_DIR"] = str(tmp_path / "data" / "index")

    upload = io.BytesIO(b"Open Notebook stores citations with source, chunk id, and snippet.")
    ingest_response = client.post(
        "/ingest",
        files={"file": ("note.txt", upload, "text/plain")},
    )
    assert ingest_response.status_code == 200, ingest_response.text

    query_response = client.post("/query", json={"query": "What does Open Notebook store?", "k": 3})
    assert query_response.status_code == 200, query_response.text
    payload = query_response.json()
    assert "answer" in payload
    assert "citations" in payload
    assert isinstance(payload["citations"], list)
    assert payload["citations"]
    assert {"source", "chunk_id", "snippet"} <= set(payload["citations"][0].keys())
