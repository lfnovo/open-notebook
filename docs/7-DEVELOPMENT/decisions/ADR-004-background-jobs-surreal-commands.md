# ADR-004: Background jobs via Surreal Commands

- **Status**: Accepted (revisit tracked in #381 — Platform v-next cluster)
- **Date**: 2026-07 (retroactive record — decision dates from the async rework)
- **Related**: #381, [ADR-001](ADR-001-surrealdb.md), [podcasts.md](../podcasts.md)

## Context

Long-running operations (podcast generation takes minutes; embedding and source processing take
seconds to minutes) must not block the API or the UI (async-first principle). A job queue was
needed — but the classic answer (Celery + Redis) adds two services to a stack whose selling point
is "one database, easy self-hosting."

## Decision

Use **[surreal-commands](https://github.com/lfnovo/surreal-commands)**: a job queue built on the
SurrealDB we already run. Commands are fire-and-forget (`submit_command()` returns an id), a
dedicated worker process executes them, and status is polled via `/commands/{id}`. Retry policy is
a blocklist (`stop_on: [ValueError]` = permanent failure; everything else retries).

## Alternatives considered

- **Celery + Redis** — battle-tested and feature-rich, but two extra services for self-hosters.
- **FastAPI BackgroundTasks / asyncio tasks** — no persistence: jobs die with the process, no
  status tracking, no retry.
- **arq / RQ (Redis-based)** — lighter than Celery but still adds Redis.

## Consequences

- Zero extra infrastructure — the queue lives in SurrealDB.
- A separate worker process is **required** for anything async to actually run (documented in the
  root `AGENTS.md`; a silent-queue failure mode when forgotten).
- Less mature than Celery: fewer scheduling/monitoring features; retry semantics are ours to
  maintain.
- A possible migration to Celery is under evaluation as part of the coordinated Platform v-next
  breaking change (#381) — if it happens, it will supersede this record.
