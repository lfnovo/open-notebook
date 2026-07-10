# Content Processing: Chunking, Embedding, Context & Encryption

Design notes for the utilities in `open_notebook/utils/` that turn raw content into searchable, LLM-consumable data. These are cross-cutting: sources, notes and insights all flow through them.

## Chunking (`utils/chunking.py`)

Content is split with content-type-aware LangChain splitters (`HTMLHeaderTextSplitter`, `MarkdownHeaderTextSplitter`, `RecursiveCharacterTextSplitter`). Content type detection uses the file extension first; heuristics can override a PLAIN extension when confidence ≥ 0.8. Oversized chunks from the HTML/Markdown splitters get a secondary split.

**Why the 400-token default.** `OPEN_NOTEBOOK_CHUNK_SIZE` defaults to 400 tokens — ~20% below the 512-token ceiling of BERT-family embedders (e.g. `mxbai-embed-large`). The buffer absorbs three error sources: tokenizer mismatch (we measure with `o200k_base`, the embedder tokenizes with WordPiece), splitter overshoot, and special tokens. For embedders with large windows (OpenAI `text-embedding-3` family: 8191 tokens) raise it, e.g.:

```bash
export OPEN_NOTEBOOK_CHUNK_SIZE=1500
export OPEN_NOTEBOOK_CHUNK_OVERLAP=150
```

`OPEN_NOTEBOOK_CHUNK_OVERLAP` defaults to 15% of chunk size. Both are **token-based** (not characters), minimum chunk size 100, and require an app restart to take effect.

## Embedding (`utils/embedding.py`)

- `generate_embedding(text)` — unified entry point: short text (≤ chunk size) embeds directly; long text is chunked, each chunk embedded, and the results combined via **mean pooling** (normalize each → mean → normalize result, numpy).
- `generate_embeddings(texts)` — batch path used by `embed_source_command`: batches of 50 with per-batch retry, to stay under provider payload limits.
- Empty/whitespace-only input raises `ValueError` — which background commands treat as a permanent (non-retried) failure by design.
- The embedding model comes from `model_manager` (see [credentials.md](credentials.md) for how provider config is resolved).

**Who triggers embedding** (see also the domain rules in `open_notebook/AGENTS.md`):

| Content | Trigger |
|---|---|
| Note | `Note.save()` auto-submits `embed_note` |
| Insight | `create_insight_command` submits `embed_insight` |
| Source | explicit `source.vectorize()` → `embed_source` (NOT automatic on save) |
| Everything | `rebuild_embeddings_command` fans out individual jobs |

All embedding is fire-and-forget through the surreal-commands worker — nothing embeds if the worker isn't running.

## Context building (`utils/context_builder.py`)

`ContextBuilder` assembles LLM context from selected sources/notes/insights under a token budget:

- Each `ContextItem` counts its own tokens on construction; `build()` adds items in priority order (default weights: insight 1.2 > source 1.0 > note 0.8) and stops once `max_tokens` is exceeded (no prorating).
- Fetching is lazy (nothing is loaded until `build()`), and every call re-fetches — there is no cache layer.
- Token counting uses `o200k_base` via tiktoken and is an estimate (±5-10% vs. the actual model); `token_count()` falls back to a coarse estimate if tiktoken is unavailable.

## Encryption (`utils/encryption.py`) {#encryption}

Field-level encryption for sensitive values (API keys) stored in the database, using Fernet (AES-128-CBC + HMAC-SHA256).

- Key source: `OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE` (Docker secrets) → `OPEN_NOTEBOOK_ENCRYPTION_KEY`. **No default** — credential storage is unavailable until the key is set.
- Any string works as key: it's derived to a Fernet key via SHA-256, lazily on first use.
- Decryption falls back gracefully: an `InvalidToken` (legacy unencrypted data) returns the original value, so pre-encryption databases keep working.
- Key rotation is **not implemented** — changing the key orphans previously encrypted values.

## Text utilities (`utils/text_utils.py`)

`clean_thinking_content()` strips `<think>…</think>` blocks from model output (extended-thinking models); used in every graph that consumes LLM responses. It handles malformed output (missing opening tag) and bypasses extraction for content > 100KB for performance.
