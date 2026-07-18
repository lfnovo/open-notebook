# ADR-001: SurrealDB as the database

- **Status**: Accepted
- **Date**: 2026-07 (retroactive record — decision dates from project inception; long-form rationale maintained in [#372](https://github.com/lfnovo/open-notebook/issues/372))
- **Related**: #372, #378, #381, [VISION.md](../../../VISION.md) (Platform v-next cluster)

## Context

Open Notebook needs document storage (sources with metadata), graph relationships (notebooks ↔ sources ↔ notes), vector embeddings for semantic search, and background jobs — while staying easy to self-host for privacy-focused users. A traditional stack would be Postgres + Redis + Celery + a vector DB: four services to operate.

## Decision

Use **SurrealDB** as the single database: documents, graph relationships, vector embeddings and (via surreal-commands) job queueing in one service. Stay with it and work through the challenges; reconsider only under the exit criteria listed in #372 (unworkable transaction conflicts, performance that tuning can't fix, unpatched critical security issue, or a mature alternative with the same consolidated benefits).

## Alternatives considered

- **PostgreSQL + pgvector** — maturity and ecosystem, but loses graph queries and still needs Celery/Redis for jobs.
- **SQLite + LiteFS** — ultimate simplicity, but poor concurrency and no graph features.
- **MongoDB + Redis + Celery** — familiar tooling, but three services kills the self-hosting simplicity advantage.
- **Hybrid (Postgres + Neo4j)** — best of both worlds at an ops cost we don't want to impose on self-hosters.

## Consequences

- One container to run — the biggest infra advantage for self-hosted users.
- Younger ecosystem: we document more and contribute back; fewer established tuning practices.
- Transaction conflicts under concurrency turned out to be log verbosity, not failures (#362, #373) — handled with Tenacity retries.
- Major-version upgrades need deliberate migration work (v3: #378, part of the Platform v-next cluster).
