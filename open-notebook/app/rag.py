from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from config import Settings, get_settings

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover
    faiss = None


def normalize_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype("float32")


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks


class Embedder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._client = None

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        provider = self.settings.embedding_provider.lower()
        if provider == "sentence-transformers":
            return self._embed_sentence_transformers(texts)
        if provider == "openai":
            return self._embed_openai(texts)
        if provider == "hash":
            return self._embed_hash(texts)
        raise ValueError(f"Unsupported embedding provider: {self.settings.embedding_provider}")

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_texts([query])

    def _embed_sentence_transformers(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.settings.embedding_model)
        vectors = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return normalize_rows(vectors.astype("float32"))

    def _embed_openai(self, texts: list[str]) -> np.ndarray:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.settings.openai_api_key)
        response = self._client.embeddings.create(
            model=self.settings.embedding_model,
            input=texts,
        )
        vectors = np.array([item.embedding for item in response.data], dtype="float32")
        return normalize_rows(vectors)

    def _embed_hash(self, texts: list[str]) -> np.ndarray:
        dim = self.settings.hash_embedding_dim
        rows = []
        for text in texts:
            vector = np.zeros(dim, dtype="float32")
            for token in text.lower().split():
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "big") % dim
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[idx] += sign
            rows.append(vector)
        return normalize_rows(np.vstack(rows))


@dataclass(slots=True)
class RetrievedChunk:
    source: str
    chunk_id: str
    snippet: str
    chunk_text: str
    score: float


def _load_meta(settings: Settings) -> list[dict[str, Any]]:
    if not settings.meta_path.exists():
        return []
    return json.loads(settings.meta_path.read_text(encoding="utf-8"))


def _save_meta(settings: Settings, entries: list[dict[str, Any]]) -> None:
    settings.meta_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _new_faiss_index(dimension: int):
    if faiss is None:
        return None
    return faiss.IndexFlatIP(dimension)


def _load_faiss_index(settings: Settings):
    if faiss is None or not settings.index_path.exists():
        return None
    return faiss.read_index(str(settings.index_path))


def _save_faiss_index(settings: Settings, index) -> None:
    if faiss is not None and index is not None:
        faiss.write_index(index, str(settings.index_path))


def _load_numpy_index(settings: Settings) -> np.ndarray | None:
    if settings.fallback_index_path.exists():
        return np.load(settings.fallback_index_path)
    return None


def _save_numpy_index(settings: Settings, vectors: np.ndarray) -> None:
    np.save(settings.fallback_index_path, vectors)


def add_documents(documents: list[dict[str, str]], settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    if not documents:
        return {"chunks_added": 0, "sources": []}

    embedder = Embedder(settings)
    texts = [doc["chunk_text"] for doc in documents]
    vectors = embedder.embed_texts(texts)
    meta = _load_meta(settings)

    if faiss is not None:
        index = _load_faiss_index(settings)
        if index is None:
            index = _new_faiss_index(vectors.shape[1])
        index.add(vectors)
        _save_faiss_index(settings, index)
    else:  # pragma: no cover
        existing = _load_numpy_index(settings)
        merged = vectors if existing is None else np.vstack([existing, vectors]).astype("float32")
        _save_numpy_index(settings, merged)

    meta.extend(documents)
    _save_meta(settings, meta)
    return {
        "chunks_added": len(documents),
        "sources": sorted({doc["source"] for doc in documents}),
    }


def retrieve(query: str, k: int = 5, settings: Settings | None = None) -> list[RetrievedChunk]:
    settings = settings or get_settings()
    meta = _load_meta(settings)
    if not meta:
        return []

    query_vector = Embedder(settings).embed_query(query)

    if faiss is not None and settings.index_path.exists():
        index = _load_faiss_index(settings)
        scores, indices = index.search(query_vector, min(k, len(meta)))
        ranked = zip(indices[0], scores[0], strict=False)
    else:  # pragma: no cover
        matrix = _load_numpy_index(settings)
        if matrix is None or matrix.size == 0:
            return []
        similarities = matrix @ query_vector[0]
        order = np.argsort(similarities)[::-1][:k]
        ranked = ((int(i), float(similarities[i])) for i in order)

    results: list[RetrievedChunk] = []
    for idx, score in ranked:
        if idx < 0 or idx >= len(meta):
            continue
        item = meta[idx]
        results.append(
            RetrievedChunk(
                source=item["source"],
                chunk_id=item["chunk_id"],
                snippet=item["snippet"],
                chunk_text=item["chunk_text"],
                score=float(score),
            )
        )
    return results


def _extractive_answer(query: str, retrieved: list[RetrievedChunk]) -> str:
    lines = [f"Question: {query}", "", "Most relevant retrieved passages:"]
    for chunk in retrieved[:3]:
        lines.append(f"- [{chunk.source}#{chunk.chunk_id}] {chunk.snippet}")
    lines.append("")
    lines.append("Configure LOCAL_MODEL_NAME, or set MODEL_PROVIDER=openai/anthropic, for generative synthesis.")
    return "\n".join(lines)


def _local_generation(prompt: str, settings: Settings) -> str | None:
    if not settings.local_model_name:
        return None
    try:
        from transformers import pipeline

        generator = pipeline("text2text-generation", model=settings.local_model_name)
        output = generator(prompt, max_new_tokens=200, do_sample=False)
        return output[0]["generated_text"].strip()
    except Exception:
        return None


def _openai_answer(prompt: str, settings: Settings) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when MODEL_PROVIDER=openai")
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "Answer using only the retrieved context and cite the sources inline."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


def _anthropic_answer(prompt: str, settings: Settings) -> str:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required when MODEL_PROVIDER=anthropic")
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=300,
        system="Answer using only the retrieved context and cite the sources inline.",
        messages=[{"role": "user", "content": prompt}],
    )
    parts = []
    for block in response.content:
        text = getattr(block, "text", "")
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def answer(query: str, k: int = 5, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    retrieved = retrieve(query, k=k, settings=settings)
    citations = [
        {"source": chunk.source, "chunk_id": chunk.chunk_id, "snippet": chunk.snippet}
        for chunk in retrieved
    ]
    if not retrieved:
        return {
            "answer": "No indexed content is available yet. Ingest files first, then query again.",
            "citations": [],
        }

    context = "\n\n".join(
        f"[{chunk.source}#{chunk.chunk_id}]\n{chunk.chunk_text}" for chunk in retrieved
    )
    prompt = (
        "Use the context below to answer the question. Prefer precise statements and mention the cited sources.\n\n"
        f"Question: {query}\n\nContext:\n{context}"
    )

    provider = settings.model_provider.lower()
    if provider == "openai":
        body = _openai_answer(prompt, settings)
    elif provider == "anthropic":
        body = _anthropic_answer(prompt, settings)
    else:
        body = _local_generation(prompt, settings) or _extractive_answer(query, retrieved)

    return {"answer": body, "citations": citations}
