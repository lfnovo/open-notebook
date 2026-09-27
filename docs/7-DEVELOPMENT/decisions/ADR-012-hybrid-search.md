# ADR-012: Local hybrid passage retrieval

Status: Accepted · 2026-09-21 · Owner: `hybrid-search` optional runtime module

## Decision

Keep SurrealDB and the installed multilingual embedding model. Add a module-owned,
disposable passage index; never rewrite original sources, notes, insights, or vectors.
Search and Ask use the same retrieval service when the module is enabled. Disabling
returns Ask to its original vector path and hides the hybrid search option. All
module preferences use the standard settings registry and optimistic revisions.
Core changes are limited to a lifecycle adapter and shared module translations;
feature changes are SHA-checked build overlays.

Flow: current scoped document IDs → Turkish/English BM25 + semantic candidates →
weighted RRF → document diversity → local BGE reranker → original IDs and excerpts.
The local reranker is independent infrastructure, authenticated, bounded, and runs
on Apple MPS when available. It receives at most 80 bounded passages, never a whole
research archive. Model weights are pinned; inference uses safetensors and no remote
model code. Module-to-model access uses existing public model interfaces.

## Index and consistency

Each model/configuration signature owns an `hs_p_<signature>` table. Two distinct
text fields/indexes are necessary: SurrealDB 2.6.5 chooses only one full-text index
when both analyzers share a field; an index hint did not force the Turkish analyzer.
Both BM25 plans and the HNSW plan are verified with EXPLAIN. Turkish case is
normalized before Snowball; punctuation/identifiers remain in original excerpts.

Original text is split into exact slices with character offsets and SHA-256,
1600 UTF-8 bytes at most, preferring newline/sentence boundaries, with overlap up
to 160 characters. This bound leaves room for retrieval instructions under the
installed EmbeddingGemma input window; it is not a universal optimal chunk size.
Document and query prompts follow that model's retrieval formats. Other embedding
models receive their ordinary input. Changing model/provider/credential identity
creates a separate generation. A same-name weight replacement without changing
configuration is an operator limitation: rebuild with a new model record/version.

Maintenance polls every 60 seconds by default. Body/title hashes detect changes;
only changed documents are embedded. One transaction replaces each document's
passages and commit marker. All statements in a multi-statement DB response are
checked: the SDK's ordinary query() returns only statement zero. A complete new
generation is published only after current document hashes match all markers.
Old generations remain available for rollback; there is no automatic destructive
pruning of original data. Operators should remove unused generations only after
validation when changing models repeatedly.

Every search reads current metadata and notebook relationships. Deleted and stale
versions are excluded BEFORE lexical/scoped-vector limits. Original IDs are checked
again after fusion; identical text in another notebook never grants access. Scoped
search uses exact cosine so global ANN post-filtering cannot starve a small scope.
Global search uses HNSW (F32, cosine, M=16, EFC=200), with exact fallback if too few
current hits remain. Exact scoped cost grows with the selected corpus; revisit with
measured filtered-ANN recall before a very large deployment.

Only query embeddings are cached (128 entries, signature+exact query), not search
results or notebook membership. No stale result cache is possible after deletion.
A shared embedding lock avoids duplicate work and bounds local model concurrency.
The reranker uses a bounded serialized GPU queue and client deadlines. Database
and embedding exceptions are visible; failure of every retriever raises an error,
not a false “no matches”.

## Ranking and evidence rules

- Turkish/English BM25 each receive half weight; vector retrieval receives one
  weight in RRF (`k=60`). Raw cosine and BM25 scales are never summed.
- SurrealDB 2.6 can return negative BM25 values for frequent terms. Candidate
  aggregation clamps the negative term contribution and retains match coverage.
- Quoted phrases and identifiers require token boundaries; `AB-123` is not
  `AB-1234`. Exact candidate matches are protected during ordering, not treated as
  proof that the document answers the question.
- Duplicate hits within one channel have one vote. Document diversity reserves
  reranker slots before adding more passages from the same document. Original
  identities remain distinct; copied content is not independent corroboration.
- Top reranker score below 0.001 triggers an abstention from neural ordering:
  retain hybrid candidates and show weak relevance. This is a conservative local
  heuristic from diagnostic testing, not a calibrated probability of truth.
- Failure of one retrieval channel or the reranker keeps usable results and shows
  which component failed. Model-space mismatch disables vector search until the
  replacement index is ready; it never mixes vectors from unlike models.
- Ask preserves the original question among at most five distinct searches, so a
  planner cannot silently remove exact identifiers. It receives at most the
  configured number of distinct documents, up to three excerpts each.
- Answer and final stages reject local document citations outside their supplied
  evidence IDs. Prompts distinguish untrusted reference text, copied material,
  conflicting evidence and weak retrieval. ID validity is not entailment checking.

## Scope and limitations

Search is over the notebook's extracted text, not an internet crawler. OCR quality,
missing transcriptions and failed source processing still limit retrieval. This
change does not silently reprocess originals or globally change chunk sizes.
No paid API keys, external vector database, browser control or new research runs
are required. Neural model quality is measured on a small reproducible synthetic
set, not asserted universally for every language/domain. Duplicate/near-duplicate
semantics and factual truth still require evidence evaluation.

The live corpus was 20 text documents / 1376 passages at rollout. Validate scoped
latency and ANN recall again as it grows. At much larger sizes, optimize metadata
change feeds, bounded document pagination and filtered ANN based on measurements;
do not add a second database merely for architectural appearance.

## Sources

- [SurrealDB hybrid search](https://surrealdb.com/blog/hybrid-search-inside-surrealdb)
- [Index and HNSW reference](https://surrealdb.com/docs/reference/query-language/statements/define/indexes)
- [Analyzer and Turkish Snowball](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer)
- [Sentence Transformers retrieve and rerank](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
- [BAAI BGE reranker model card](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- [Google EmbeddingGemma model card and retrieval prompts](https://huggingface.co/google/embeddinggemma-300m)
