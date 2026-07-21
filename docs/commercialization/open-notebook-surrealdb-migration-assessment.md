# Open Notebook — SurrealDB Migration Assessment

**Decision:** Keep SurrealDB (zero effort) vs. migrate to PostgreSQL + pgvector
**Prepared for:** Engineering / leadership build-vs-buy decision
**Scope:** Fork of `lfnovo/open-notebook` (v1.10.0) intended for commercial use

---

## Executive summary

SurrealDB's license (BSL 1.1) **already permits our intended commercial use** — embedding it inside a product we ship or host. It is *not* a legal blocker. The only forbidden use is reselling SurrealDB itself as a managed database service, which is not our business.

Migrating off SurrealDB is therefore **optional** — a license-posture choice, not a requirement — and it is expensive. Based on a full trace of the codebase, a migration to PostgreSQL + pgvector is an estimated **6–10 engineer-weeks** with two high-risk workstreams (search parity and replacing the job system). It delivers **no end-user benefit**; the product behaves identically afterward.

**Recommendation: keep SurrealDB.** Document it in a third-party notices file and proceed. Revisit only if a hard "OSI-approved licenses only" policy is imposed by legal or a customer contract.

---

## Why keeping it is legally fine

SurrealDB's BSL 1.1 grant allows: use at any scale, embedding in applications shipped to customers, running it as the backend of a hosted service, and internal use. The sole restriction is offering SurrealDB *as a commercial database-as-a-service*. Four years after each release, the version converts to Apache 2.0.

Notably, common "alternatives" are **more** restrictive, not less: ArangoDB (BSL + 100 GB Community cap + no distribution-with-your-software) and MongoDB (SSPL, not OSI-approved) would both be a step backward for this use case.

---

## How deeply the code depends on SurrealDB

Evidence from the v1.10.0 source tree (~20,000 lines of Python across 87 files):

| Coupling point | Location | Size / count | Migration difficulty |
|---|---|---|---|
| Connection + query wrapper | `open_notebook/database/repository.py` | 207 lines | **Low** — single choke point |
| ORM base (`ObjectModel`) | `open_notebook/domain/base.py` | 361 lines | **Medium** — rewrite CRUD onto SQL |
| Raw query call sites | 18 files | **121 calls** | **Medium** — most are CRUD, some are graph |
| Graph relations (edge tables) | `domain/notebook.py` | `artifact`, `reference`, `refers_to` + traversals | **High** — native graph feature |
| Full-text + vector search | DB-stored `fn::text_search`, `fn::vector_search` | 6 BM25 indexes, custom analyzer, cosine vectors | **High** — hardest to reproduce with parity |
| Background job system | `surreal-commands` + `commands/` | 4 job modules (~60 KB), 11 touchpoints | **High** — must replace the whole runner |
| Schema migrations | `database/migrations/*.surrealql` | **15 migrations**, incl. triggers/events | **Medium** — re-express as SQL/Alembic |
| Existing user data | Live SurrealDB instances | — | **Medium** — one-time ETL |

### What makes three of these genuinely hard

1. **Search lives inside the database.** The full-text and vector search algorithms are SurrealQL *stored functions*, not Python. They rely on a custom analyzer (snowball/English tokenizers), 6 BM25 indexes with highlighting, and cosine similarity over `array<float>` columns, with result fusion across sources, notes, and insights. Rebuilding this on Postgres means `tsvector`/`ts_rank_cd`/`ts_headline` for full-text plus pgvector `<=>` for vectors, then re-tuning until results match. Verifying parity is the bulk of the risk.

2. **The job queue is the database.** `surreal-commands` stores and runs background jobs (embedding, podcast generation, source processing) *in* SurrealDB. Removing SurrealDB removes the job runner entirely, so it must be replaced with Celery/Arq + a broker (Redis) or a Postgres-based queue, and all four command modules plus 11 submit/status call sites rewired.

3. **Graph edges are native.** Relationships between notebooks, sources, and notes use SurrealDB edge tables and traversal syntax (`->reference`, `<-reference.in`, `->refers_to`). On Postgres these become explicit join tables with JOINs / recursive CTEs (or the Apache AGE extension) — a real re-design of those queries.

---

## Effort estimate — migrate to PostgreSQL + pgvector

One competent engineer fluent in Python + Postgres:

| Workstream | Estimate | Risk |
|---|---|---|
| Rewrite repository + connection layer (asyncpg / SQLAlchemy + pgvector) | 3–5 days | Low |
| Rewrite ORM base + 121 call sites across 18 files | 5–8 days | Medium |
| Re-design graph relations as join tables / CTEs | 3–5 days | Medium-High |
| Rebuild full-text + vector search and verify parity | 5–8 days | **High** |
| Replace `surreal-commands` with Celery/Arq + broker; rewire jobs | 5–8 days | **High** |
| Convert 15 migrations to SQL/Alembic + triggers | 2–4 days | Medium |
| Data-migration ETL (RecordIDs → UUIDs/FKs, re-embed) | 2–3 days | Medium |
| Integration + regression testing, search-parity fixes | 5–8 days | High |
| Docker/compose/infra (drop Surreal, add Postgres+pgvector, add Redis) | 1–2 days | Low |
| **Total** | **~31–51 engineer-days (≈ 6–10 weeks)** | — |

With two engineers splitting the data-layer and job-system tracks, calendar time compresses to roughly **4–6 weeks**, not effort.

*Note:* ArcadeDB (Apache-2.0, native multi-model) would reduce the graph/search re-design somewhat but still requires rewriting every query and replacing the job system, on a smaller ecosystem. It does **not** meaningfully beat Postgres here.

---

## The alternative: keep SurrealDB

**Effort: ~0.5 day.** Add a `THIRD-PARTY-NOTICES` entry recording SurrealDB's BSL 1.1 and its DBaaS restriction; confirm with legal that the product is not a database service (it is not). No code changes. No end-user difference.

---

## Bottom line

| Path | Cost | End-user benefit | Residual risk |
|---|---|---|---|
| **Keep SurrealDB (BSL)** | ~0.5 day | None (identical product) | Source-available dependency; converts to Apache 2.0 over time |
| **Migrate to Postgres + pgvector** | 6–10 eng-weeks | None | Search-parity and job-system rewrite risk |

The migration buys a license *label* (OSI-approved) at the price of two months of the highest-risk engineering in the codebase, with zero product improvement. Recommend keeping SurrealDB unless an external policy forces the change — in which case the target is PostgreSQL + pgvector and this table is the plan.

*This is a technical assessment, not legal advice; have counsel confirm the BSL position for the specific commercial model.*
