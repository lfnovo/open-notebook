# Hybrid search

Optional local retrieval module for both Search and Ask. It uses original IDs and
an additive passage index in SurrealDB; original text and vectors are preserved.
The module can be disabled at runtime through Settings → Modules settings. It has
candidate, reranking, Ask-context and indexing-interval settings.

Include `hybrid-search` in `scripts/prepare_modules.py --modules ...`. The API
starts maintenance for installed/enabled modules. Search shows index progress,
passage counts, latency and degraded-mode feedback. “Refresh index” schedules an
idempotent incremental refresh, not deletion or replacement of original data.

A private local reranker service must be installed separately. Create a venv with
`reranker/requirements.lock`; download BAAI/bge-reranker-v2-m3 at a pinned revision
with safetensors into a private directory. `config.json` contains `model_path`
(absolute directory) and `revision`; `.key` contains a random shared secret with
mode 0600. Start `uvicorn server:app` with `RERANKER_ROOT` set to that directory.
Use port 8321; bind to the loopback/VM-reachable interface required by your host.
The notebook reads `LOCAL_RERANKER_URL` (default `http://host.lima.internal:8321`)
and `LOCAL_RERANKER_KEY_FILE` (default `data/hybrid-search/reranker.key`). Keep these
private files outside Git. Inference has no paid API and never downloads remote
code. If unavailable, hybrid fusion still returns results with a visible warning.

Embedding generation uses the notebook's current embedding model. Existing model
selection is retained. Do not switch embedding weights under an unchanged model
identity; use a new model record to obtain a separate generation. The original
index and model are never silently rebuilt or discarded.

Tests: `python -m unittest discover -s modules/hybrid-search/tests -p test_ranking.py`;
application environment: `pytest modules/hybrid-search/tests/test_service.py`.
`integration.py` requires a disposable database name starting `hybrid_validation_`,
local Ollama EmbeddingGemma and the authenticated reranker; it clears only its test
fixture tables. It tests actual SurrealQL plans, notebook isolation, stale/delete
behavior and 30 multilingual retrieval questions. Never point it at live data.

See [ADR-012](../../docs/7-DEVELOPMENT/decisions/ADR-012-hybrid-search.md) for invariants,
fallback rules, model limits and trade-offs. Index files are derivative data; schema
rollback is disabling the module and restoring the prior application code. Preserve
`hs_state` and original database backups until the replacement has been validated.

Large document maintenance stages writes in groups of at most 16 passages and
256 KiB of serialized input. Search admits a new version only after its complete
publication marker is committed; interrupted cleanup resumes on the next pass.
Original notes/sources are never altered. See
[ADR-027](../../docs/7-DEVELOPMENT/decisions/ADR-027-bounded-index-publication.md).
`tests/bounded_integration.py` exercises 3,386 synthetic passages with injected
interruption against an isolated SurrealDB 2.6 instance, without model calls.
It requires the exact disposable database URL/name asserted in that script and
real BM25/HNSW indexes. Allow the database the normal deployment memory budget;
small write transactions do not eliminate index and read memory requirements.
