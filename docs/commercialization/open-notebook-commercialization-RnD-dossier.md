# Open Notebook — Commercialization R&D Dossier

**Project:** `lfnovo/open-notebook` (v1.10.0) — evaluated as the base for a commercial product
**Purpose:** Full due-diligence findings for a go / no-go and licensing decision
**Prepared by:** Engineering (R&D)
**Status:** Complete — ready for leadership decision

---

## 1. What Open Notebook is (plain English)

Open Notebook is an open-source, privacy-focused alternative to Google's NotebookLM. A user uploads research material — PDFs, web pages, videos, audio, Office documents — and the tool lets them search it, chat with it using AI, generate summaries and insights, and even produce multi-speaker podcasts from it. Its selling point over Google's version is privacy and control: it can run entirely on infrastructure we control, and it works with 18+ AI providers rather than locking users into one.

It is a mature, actively maintained project: roughly 20,000 lines of Python across 87 files, a modern web front-end, and a clean, layered architecture. It is a credible foundation to build a commercial product on.

---

## 2. Headline verdict: can we commercialize it?

**Yes.** The project and virtually all of its building blocks use permissive licenses (MIT / BSD / Apache) that explicitly allow selling a closed, commercial product without publishing our source code.

There is **one component to be deliberate about** — the SurrealDB database — which uses a "source-available" license rather than a fully open one. It permits our use, but it is the single item that needs a conscious decision (covered in Section 7). Everything else is clear.

---

## 3. Technology stack at a glance

| Layer | Technology | Why it's there |
|---|---|---|
| Web front-end | Next.js / React / TypeScript | The user interface |
| Backend API | Python + FastAPI | The application server and business logic |
| Database | **SurrealDB** | Stores everything; also powers search and relationships |
| Background jobs | `surreal-commands` | Runs slow tasks (embedding, podcasts) without freezing the app |
| AI model access | `esperanto` + LangChain | One interface to 18+ AI providers |
| Content ingestion | `content-core` | Extracts text from PDFs, video, audio, web, Office files |
| Podcast engine | `podcast-creator` | Generates multi-speaker audio |
| AI orchestration | LangChain + LangGraph | Chat, Q&A, and multi-step AI workflows |

Note: three of the core building blocks (`esperanto`, `content-core`, `podcast-creator`, plus `ai-prompter` and `surreal-commands`) are written by the **same author** as Open Notebook itself, and all are MIT-licensed. This is convenient (consistent, permissive) but also a concentration point (Section 6).

---

## 4. Feature-by-feature breakdown (what each feature is, what powers it, and any caution)

| Feature | What it does | What powers it | Dependency license | Caution |
|---|---|---|---|---|
| Multi-notebook organization | Manage multiple research projects, sources, and notes | SurrealDB (document storage) | BSL 1.1 | See §7 |
| Universal content ingestion | Extract text from PDF, video, audio, web pages, Office docs | `content-core` | MIT | None |
| Multi-model AI (18+ providers) | Use OpenAI, Anthropic, Google, Groq, Mistral, Ollama, DeepSeek, LM Studio, etc. | `esperanto` + `langchain-*` provider packages | MIT | Each provider's **API terms** apply to our commercial use (§6) |
| Chat with context | AI conversation grounded in the user's research | LangChain + LangGraph | MIT | Chat state stored via LangGraph SQLite checkpoint |
| Transformations & insights | Auto-summaries, extractions, custom AI actions | LangChain + `ai-prompter` + chosen model | MIT | None |
| Full-text search | Keyword search across all content | SurrealDB BM25 + custom analyzer + stored `fn::text_search` | BSL 1.1 | Search logic lives *inside* the DB (§7) |
| Semantic / vector search | Meaning-based search | SurrealDB vector search + embedding model + `fn::vector_search` | BSL 1.1 | Requires an embedding model configured |
| Content relationships | Links between notebooks, sources, and notes | SurrealDB graph edges (`reference`, `refers_to`, `artifact`) | BSL 1.1 | Native graph feature (§7) |
| Podcast generation | Multi-speaker audio from research | `podcast-creator` + TTS provider | MIT | Depends on external TTS provider terms |
| Background processing | Runs embedding, podcast, and ingestion jobs asynchronously | `surreal-commands` (built on SurrealDB) | MIT (library) / BSL (engine) | Job system is coupled to SurrealDB (§7) |
| Credential security | Encrypts stored API keys | App-level encryption key | MIT | We must set/manage the encryption key in production |

---

## 5. Full dependency license inventory

**Application code and libraries — all permissive, all commercial-safe:**

| Component | License | Commercial-safe |
|---|---|---|
| open-notebook (core) | MIT | ✅ |
| content-core, podcast-creator, esperanto, ai-prompter, surreal-commands | MIT | ✅ |
| surrealdb (Python client), langchain-google-genai (Apache deps) | Apache-2.0 | ✅ |
| fastapi, uvicorn, pydantic, loguru, langchain, langgraph, tiktoken, all `langchain-*` | MIT | ✅ |
| httpx, python-dotenv, babel, numpy | BSD-3-Clause | ✅ |
| **pycountry** | **LGPL-2.1** | ✅ *if unmodified* — see §6 |
| Front-end: Next.js, React, Radix UI, Monaco, KaTeX, TanStack Query, zod, zustand, i18next | MIT / ISC | ✅ |

**Infrastructure — the one to decide on:**

| Component | License | Notes |
|---|---|---|
| **SurrealDB (database engine)** | **BSL 1.1 (source-available, not OSI open-source)** | Permits our use; see §7 |

---

## 6. Cautions and risks to be aware of

1. **SurrealDB is source-available, not fully open source.** This is the one strategic item — full detail and the decision in Section 7. It does *not* block commercial use of our product; it only forbids reselling SurrealDB itself as a hosted database service, which is not our business.

2. **`pycountry` is LGPL (weak copyleft).** Safe to use as a normal dependency in a commercial product. The only rule: do **not** modify pycountry's own source code. Use it as-is and there is no obligation.

3. **We must rebrand.** The MIT license gives us the code, not the name "Open Notebook," its logo, or the open-notebook.ai brand. We ship under our own name and assets.

4. **AI provider API terms apply downstream.** The code is ours to use, but when the product calls OpenAI, Anthropic, Google, etc., each provider's commercial terms of service govern that usage. This is a normal cost/compliance item for any AI product, not specific to Open Notebook.

5. **"AS IS" — no warranty.** Open-source licenses disclaim all warranty. If something fails, there is no vendor to hold liable. This is why we must own a proper testing and QA layer before selling it (see checklist §8).

6. **Maintainer concentration.** Six of the core building blocks are written by a single author. This is convenient and consistently MIT-licensed, but it is a bus-factor consideration: if that author steps away, we may need to maintain those libraries ourselves. Because they are MIT, we are legally free to fork and maintain them — so this is a resourcing risk, not a legal one.

7. **`surreal-commands` (the job system) is a small third-party library.** It works, but it is tied to SurrealDB and is a minor dependency. If we ever migrate off SurrealDB, this must be replaced (Section 7).

---

## 7. The one strategic decision: SurrealDB

Everything above is settled. This is the only real choice, and it is a business/legal decision, not a technical one.

**The situation:** SurrealDB uses the Business Source License (BSL 1.1). It is source-available, not OSI-certified open source. Its terms allow us to embed it in our product, ship that product to customers, and run it as a hosted service at any scale. The *only* prohibited use is selling SurrealDB itself as a managed database service — which we are not doing. Four years after each release, the version we use automatically converts to the fully-open Apache 2.0 license.

**This is a decision tree, and the order matters:**

**Step 1 — Legal/compliance answers one question:** *Is a source-available dependency acceptable for our commercial model?* (Key sub-question: are we offering a database-as-a-service? Answer: no.)

- **If acceptable → KEEP SurrealDB.** Effort: ~half a day (add a third-party notices entry). No code change, no product difference. **This is the recommended path.**

- **If not acceptable (e.g., a hard "OSI-approved licenses only" policy, or a customer contract demands it) → MIGRATE.** This is where leadership makes a real call, because migration costs **6–10 engineer-weeks** with no user-visible benefit — it only changes a license label.

**If migration is required, the target is PostgreSQL + pgvector** (fully open, huge ecosystem, managed hosting everywhere, easy to hire for). ArcadeDB (also fully open, Apache 2.0) is a secondary option that keeps a native graph model, but has a smaller, self-hosted-only ecosystem and does not reduce the migration cost — so it only wins if the product's future becomes genuinely graph-centric.

**Why migration is expensive** (three unavoidable rewrites, regardless of target):
- The entire data layer is written in SurrealDB's own query language — every query must be rewritten.
- Search is implemented *inside* the database — it must be rebuilt and re-tuned to match behavior.
- The background-job system runs *on* SurrealDB — it must be replaced with a standard queue (e.g., Celery/Arq).

| Path | Cost | User benefit | When to choose |
|---|---|---|---|
| **Keep SurrealDB** | ~0.5 day | None (identical product) | Default — unless a policy forbids source-available |
| **Migrate to Postgres + pgvector** | 6–10 eng-weeks | None | Only if legal/contract mandates OSI-only |

---

## 8. Pre-launch compliance checklist

Regardless of the SurrealDB decision, these are the actions required to ship the product legally and safely:

- [ ] Keep the original MIT `LICENSE` file and copyright intact; add our own copyright line alongside (never replace).
- [ ] Generate a `THIRD-PARTY-NOTICES` file listing every dependency and its license (satisfies attribution across the whole stack in one place).
- [ ] Record SurrealDB's BSL 1.1 in that notices file; if we build our own container image bundling SurrealDB, include the BSL text.
- [ ] Do **not** modify `pycountry` source (keeps LGPL obligation at zero).
- [ ] Rebrand: new product name, logo, and assets; remove Open Notebook branding.
- [ ] Add automated license scanning to the build pipeline (`pip-licenses` for Python, `license-checker` for the front-end) to catch any future copyleft dependency sneaking in via an update.
- [ ] Review and accept the terms of service for each AI provider we enable commercially.
- [ ] Set up our own production encryption key management for stored credentials.
- [ ] Build a test/QA safety net before launch (the "AS IS" clause means quality is entirely on us).
- [ ] Obtain formal legal sign-off — specifically on the SurrealDB BSL question.

---

## 9. Bottom line for the decision-maker

Open Notebook is a strong, maintainable, permissively-licensed foundation for a commercial NotebookLM alternative. **We can commercialize it.** The only real decision is one database dependency (SurrealDB), and even that permits our use — the choice is purely about whether we want a source-available component in the stack.

- **Recommended:** keep SurrealDB, complete the compliance checklist, rebrand, and build. Fastest path to market, no downside for the product.
- **Only if a licensing policy forbids source-available software:** budget 6–10 engineering weeks to migrate to PostgreSQL, understanding it buys a license label and nothing the customer will ever see.

*This dossier is a technical and licensing assessment, not formal legal advice. Final commercialization should be confirmed with legal counsel, particularly on the SurrealDB BSL position for our specific business model.*
