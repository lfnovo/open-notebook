# ADR-010: Stream chat tokens through the graph, with an async checkpointer bridge

- **Status**: Proposed
- **Date**: 2026-11-23
- **Related**: #1412, #1332, [architecture.md](../architecture.md), `api/routers/_sse.py`, `open_notebook/utils/checkpointing.py`

## Context

Chat answers used to reach the client as one blob at the end of the turn. We want them token-by-token, and we want a Stop button that actually stops the provider request instead of only detaching the reader.

The chat is a LangGraph graph on a `SqliteSaver` checkpointer, and both properties are deliberate: the node gains loops and tools, and anything generated outside the graph would not go through them. But two properties of the existing graph block streaming:

1. The node is synchronous and the checkpointer is sync-only, so `graph.astream()` raises `NotImplementedError` on the first checkpoint call.
2. `provision_langchain_model()` builds Esperanto models with `streaming` unset, and Esperanto passes `streaming=False` explicitly — langchain-core then silently falls back to one whole-message chunk.

The first draft of this work streamed `model.astream()` from the router and wrote checkpoints by hand with `update_state(as_node=…)`, bypassing the graph. That duplicated the prompt, the node's error classification and the persistence rules, and would drift as the graph grows.

## Decision

**Generation stays in the graph. The endpoint consumes `graph.astream(..., stream_mode="messages")` and forwards the node's deltas.**

- `call_model_with_messages` is `async`, provisions with `streaming=True`, and awaits `ainvoke`. Cancelling the consumer closes the provider request.
- `HybridSqliteSaver` (`open_notebook/utils/checkpointing.py`) subclasses `SqliteSaver` and delegates each async method to the sync one on a worker thread. The module-level sync connection, and every sync `get_state`/`update_state` caller, keep working; the file-based store is not migrated.
- The endpoint persists the question before generation so a stop during prefill cannot lose it, and settles a turn that ends early: a partial answer is written with `update_state(as_node=NODE_NAME)`, an answerless turn drops the question.
- `AIMessageChunk` deltas are forwarded; a complete `AIMessage` is only forwarded when no deltas were produced (non-streaming model). `ThinkingFilter` strips `thinking` markup across chunk boundaries before anything reaches the client.

## Alternatives considered

- **Stream the model from the router (the first draft)** — simpler, but duplicates the node: prompt rendering, error classification and checkpoint writes all have to be re-derived and kept in step. Rejected on maintenance grounds; the graph route costs one class and one prompt-builder, and the probe showed it needs no node change.
- **`AsyncSqliteSaver` + `aiosqlite`** — the "proper" async checkpointer, but it wants its own async connection and would strand the module-level sync connection that every other caller uses. Two connections to one file, with the sync one still in use, was a larger change than the delegation class.
- **Poll the checkpoint until the answer appears** — no tokens while generating, which is the problem being solved.
- **A per-turn cancel endpoint** — would give a settlement acknowledgement, but it cannot cancel during prefill as promptly as closing the stream does, and adds API surface. The client instead polls the thread after aborting until the stopped turn is persisted.

## Consequences

- Stop cancels generation; a disconnect is detected by polling `request.is_disconnected()` every second, independent of token flow.
- A streamed turn and a buffered turn produce identical history, and `/api/chat/execute` still works for API consumers.
- The `thinking` filter is heuristic: a tagless preamble longer than 400 characters is shown before it is recognised, and the `complete` event (or the refetch after a stop) replaces the bubble with the cleaned text.
- Sync callers of the checkpointer still block the event loop for the duration of one SQLite write; unchanged from before, and small next to the model call.
- When the source-chat graph is converted (see #1332), it should import `HybridSqliteSaver` rather than copy it.