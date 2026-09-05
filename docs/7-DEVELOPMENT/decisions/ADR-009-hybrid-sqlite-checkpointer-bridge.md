# ADR-009: Async checkpointer via a sync SqliteSaver thread bridge

- **Status**: Accepted
- **Date**: 2026-09
- **Related**: #1264 (source-chat SSE keepalive + server-side cancellation), [ADR-004](ADR-004-background-workers.md) (worker-isolated long-running work)

## Context

To cancel source-chat generation when a client disconnects (#1264), the graph had to run on langgraph's async path (`ainvoke`/`aupdate_state`), which requires an async checkpointer. The existing checkpointer is `SqliteSaver`, which is sync-only: its async methods raise `NotImplementedError`. Switching to a genuinely async SQLite checkpointer would add a dependency and a second persistence format to reason about, while a second kind of checkpointer for one graph invites drift between the chat and source-chat graphs.

## Decision

**Wrap the existing sync `SqliteSaver` in a thin `HybridSqliteSaver` that delegates each async method to the corresponding sync method on a worker thread (`asyncio.to_thread`), and keep the module-level `sqlite3.connect(..., check_same_thread=False)` connection and all sync `get_state` callers unchanged.**

Concurrency safety comes from `SqliteSaver` itself, not from this bridge: it holds an internal `threading.Lock` and funnels every read/write through a `cursor()` context manager that acquires that lock. So even though the `to_thread` delegates can run on different worker threads at once, only one thread ever touches the single shared SQLite connection at a time — the serialization invariant the async path needs.

The async/event-loop and thread boundaries stay clean: the model node runs as a cancellable `asyncio` task on the loop; only the checkpoint I/O crosses to a worker thread, and the per-session `asyncio.Lock` in the router serializes the snapshot → append → invoke sequence per conversation.

## Alternatives considered

- **Dedicated async checkpointer (`AsyncSqliteSaver` / `aio-sqlite`)** — rejected: adds a dependency, a second checkpoint format, and a second persistence path to test, for no benefit over the sync saver since the DB work is already lock-serialized and short.
- **Run the whole graph synchronously in a thread** — the pre-existing approach — rejected: it made the model call uncancellable, which is exactly the gap #1264's follow-up needed to close.
- **A single global `asyncio.Lock` around all checkpointer calls** — rejected as redundant: `SqliteSaver` already serializes access internally; a second lock in front would add contention without adding correctness. The per-session lock in the router is a different concern (read-modify-write atomicity across `get_state` + `aupdate_state` + `ainvoke`), and it lives there rather than in the saver.

## Consequences

- One checkpointer type and one SQLite file serve both the chat and source-chat graphs; the async path is a small delegation layer, not a second persistence implementation.
- Any future checkpointer API surface must keep the `aget`/`aget_tuple`/`aput`/`aput_writes`/`alist` delegation in sync with `SqliteSaver`'s sync surface; if langgraph adds new async methods, the bridge raises `NotImplementedError` until extended.
- Correctness depends on `SqliteSaver`'s internal `threading.Lock` continuing to guard every connection access. If that upstream guarantee ever changed, this bridge would need its own lock or a real async saver.
