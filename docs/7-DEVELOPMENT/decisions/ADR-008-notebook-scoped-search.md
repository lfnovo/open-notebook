# ADR-008: Notebook scope is an optional filter on the existing search functions

- **Status**: Accepted
- **Date**: 2026-09
- **Related**: #574 and #87 (the two requests this resolves), [#1315](https://github.com/lfnovo/open-notebook/discussions/1315) (Evidence-Centered Research — the larger retrieval contract), [ADR-006](ADR-006-migration-granularity.md) (migration granularity)

## Context

Search and Ask always ran against the whole knowledge base, and `notebook_id` was accepted by `POST /api/search` but silently ignored because the request model never declared it. Two long-standing requests (#574, API; #87, UI) asked for the same thing: limit Search and Ask to one or more notebooks. Discussion #1315 places scoped retrieval inside a broader design — a retrieval contract shared by Search, Ask and chat, an evidence bundle, validated citations. That design is deliberated until October 2026 and will land in stages, so the question was whether to wait for it or ship the filter now.

## Decision

**Ship notebook scope as an optional, backward-compatible filter on the existing SurrealQL search functions, exposed on both endpoints and the Search/Ask page. Treat it as the first, smallest block of #1315, not a competing design.**

Semantics:

- The scope is a **set of notebook ids**. Empty or absent means the whole knowledge base — the historical behavior, unchanged.
- A source matches when it is linked to **any** selected notebook (`reference` edge); a note when linked via the `artifact` edge. Source chunks and insights follow their parent source. Membership is resolved once per call, not per row.
- The scope lives **in the database functions** (`fn::text_search`, `fn::vector_search`) as a trailing `option<array<record<notebook>>>` parameter, so text search, vector search and every Ask fan-out apply the same rule. The previous call shapes still work.
- The API accepts both `notebook_ids` (list, at most 50) and `notebook_id` (single — the shape #574 proposed and clients already send); they are merged. Ids are validated in the domain layer before the query: malformed → 400, unknown → 404, so a typo never looks like "no matches".
- Search and Ask on the page share one selector and one scope state.

## Alternatives considered

- **Wait for the #1315 retrieval contract** — rejected: the need is confirmed and years old, and the filter is orthogonal to how evidence is bundled or cited. The contract will consume the same `notebook_ids` parameter.
- **Filter in Python after the query** — rejected: the SurrealQL functions apply `LIMIT` before returning, so post-filtering would starve scoped results and waste the FTS/vector work.
- **Single `notebook_id` only** — rejected: #87 asked for multi-select, and a list subsumes the single case. The single field stays as a convenience for existing clients.
- **Per-notebook embedding tables** (proposed on #87) — rejected: an index-layout change for a filter; out of scope, and #1315 may revisit indexing on its own terms.

## Consequences

- Adding "notebook plus specific sources" or other scope dimensions later means extending the parameter list of the same functions (new migration), not a new engine.
- Any new caller of the search functions can ignore the scope and keep global behavior; callers that need scope pass the same list. Chat context (#1315 "Auto" option) can reuse `resolve_notebook_scope` and the functions as-is.
- The migration follows ADR-006: one migration (24), with a `_down` restoring the previous definitions.
