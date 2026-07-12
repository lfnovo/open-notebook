# Open Notebook Prototype

This directory contains a self-hosted prototype for document ingestion, retrieval, and citation-aware question answering. It is intentionally small, local-first, and easy to run.

## Scope

- Ingest local text, markdown, HTML, and PDF files.
- Optionally ingest a YouTube URL by downloading audio and transcribing it.
- Build embeddings with `sentence-transformers` by default.
- Store vectors in a file-based FAISS index by default.
- Expose a FastAPI query API and a tiny browser UI.
- Return answers with structured citations:
  - `source`
  - `chunk_id`
  - `snippet`

## Quickstart

1. Copy the environment file.

```bash
cd open-notebook
cp .env.example .env
```

2. Start the prototype.

```bash
docker compose up --build
```

3. Open the UI.

`http://localhost:8000`

4. Ingest local data.

```bash
docker compose exec app python ingest.py ingest_dir --dir /workspace/data
docker compose exec app python ingest.py ingest_file --path /workspace/data/example.txt
```

5. Ingest YouTube content.

```bash
docker compose exec app python ingest.py ingest_youtube --url "https://www.youtube.com/watch?v=..."
```

6. Query the API.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What does the document say?","k":5}'
```

## Providers

- Defaults:
  - `EMBEDDING_PROVIDER=sentence-transformers`
  - `VECTOR_STORE=faiss`
  - `MODEL_PROVIDER=local`
- Optional remote providers:
  - `MODEL_PROVIDER=openai`
  - `MODEL_PROVIDER=anthropic`
- Keep API keys only in environment variables.

## Notes and limitations

- The default local mode is intentionally lightweight. If no local generation model is configured, the API falls back to a citation-grounded extractive answer.
- YouTube transcription requires `yt-dlp` and Whisper support inside the container.
- FAISS is file-based in this prototype. No distributed index or database migrations are included.
- This is a prototype. It does not include authentication, tenancy, advanced scheduling, or production hardening.

## Security and license note

- Do not place secrets in source control.
- Review transcribed or uploaded content before using it in sensitive workflows.
- Reuse follows the repository license at the root of this repository.
