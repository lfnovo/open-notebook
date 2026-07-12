from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


@dataclass(slots=True)
class Settings:
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    model_provider: str = "local"
    local_model_name: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"
    vector_store: str = "faiss"
    top_k: int = 5
    chunk_size: int = 3000
    chunk_overlap: int = 500
    data_dir: Path = ROOT_DIR / "data"
    index_dir: Path = ROOT_DIR / "data" / "index"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    hash_embedding_dim: int = 256

    @property
    def index_path(self) -> Path:
        return self.index_dir / "index.faiss"

    @property
    def fallback_index_path(self) -> Path:
        return self.index_dir / "index.npy"

    @property
    def meta_path(self) -> Path:
        return self.index_dir / "index_meta.json"


def get_settings() -> Settings:
    data_dir = Path(os.getenv("DATA_DIR", str(ROOT_DIR / "data"))).expanduser()
    index_dir = Path(os.getenv("INDEX_DIR", str(data_dir / "index"))).expanduser()
    settings = Settings(
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "sentence-transformers"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        model_provider=os.getenv("MODEL_PROVIDER", "local"),
        local_model_name=os.getenv("LOCAL_MODEL_NAME", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        vector_store=os.getenv("VECTOR_STORE", "faiss"),
        top_k=int(os.getenv("TOP_K", "5")),
        chunk_size=int(os.getenv("CHUNK_SIZE", "3000")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "500")),
        data_dir=data_dir,
        index_dir=index_dir,
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        hash_embedding_dim=int(os.getenv("HASH_EMBEDDING_DIM", "256")),
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.index_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
