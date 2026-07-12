from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from config import Settings
from ingest import ingest_file


def test_ingest_file_creates_metadata_and_index(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    index_dir = data_dir / "index"
    data_dir.mkdir(parents=True)
    index_dir.mkdir(parents=True)
    sample = data_dir / "sample.txt"
    sample.write_text("Alpha beta gamma delta " * 200, encoding="utf-8")

    settings = Settings(
        embedding_provider="hash",
        embedding_model="hash",
        model_provider="local",
        vector_store="faiss",
        data_dir=data_dir,
        index_dir=index_dir,
    )

    result = ingest_file(sample, settings=settings)

    assert result["chunks_added"] >= 1
    assert settings.meta_path.exists()
    assert settings.index_path.exists() or settings.fallback_index_path.exists()
