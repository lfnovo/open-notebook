# Kbase — Corporate Knowledge Base Platform

**Vision:** A self-hosted, centralized knowledge base that consolidates company information scattered across SaaS tools and employee personal accounts into a single, AI-queryable system owned by the organization.

**For:** Employees, product managers, business stakeholders, and AI coding agents operating within a mid-size company (50–500 users).

**Solves:** Corporate knowledge is fragmented — meeting notes live in personal ChatGPT/NotebookLM accounts, product specs in Notion, reports in SharePoint, research in Airtable, business rules buried in code. No single place to query it all. Information leaves the company when employees leave.

---

## Goals

- **G1** — Zero knowledge leakage: all documents and AI-processed knowledge stored in company-controlled infrastructure, not employee personal accounts.
- **G2** — Single query surface: any employee or AI agent can query the full knowledge base with a single request and get a grounded, traceable answer.
- **G3** — Self-sustaining KB: content ingested from external sources (file upload + connectors) keeps the KB current without manual copying.
- **G4** — AI agent integration: coding agents (Cursor, Copilot, Claude) can query the KB via MCP to retrieve business rules, domain context, and validation constraints.

---

## Tech Stack

**Core (inherited from open-notebook base):**

- Framework: Next.js 16 + React 19 (frontend)
- API: FastAPI (Python 3.11+)
- Database: SurrealDB v3 (metadata + graph)
- AI orchestration: LangGraph
- Embeddings/LLM: Esperanto (multi-provider abstraction)

**Added for Kbase:**

- Knowledge Graph: LightRAG (graph-based RAG over workspace content)
- Document ingestion: RAGAnything (multi-modal document parsing)
- Connector layer: Airweave (open-source, MIT — 50+ pre-built connectors)
- Auth: Clerk (SSO/OIDC + email, fastest path to corporate auth)
- Vector store: SurrealDB vector fields (existing) — evaluate Vespa for scale

**Key dependencies:**

- `lightrag-hku` — knowledge graph construction and hybrid retrieval
- `airweave-sdk` — connector orchestration (Notion, GDrive, SharePoint, Airtable, GitHub)
- `@clerk/nextjs` — authentication and organization management
- `ragAnything` — PDF, PPTX, image, table-aware ingestion

---

## Scope

**v1 includes:**

- User authentication via Clerk (SSO/OIDC + email invite)
- Workspace management: create, name, set visibility (private / shared)
- Community workspaces: workspaces owned by a group/team, discoverable by members
- File upload ingestion: PDF, TXT, DOCX, MD — processed through RAGAnything
- Per-workspace knowledge graph built with LightRAG (isolated graph per workspace)
- Hybrid search: vector similarity + graph traversal + keyword
- Chat interface: ask questions scoped to one or multiple workspaces
- Note creation from chat answers (inherited from open-notebook)
- MCP server: expose workspace KB as a tool for AI coding agents
- Role model: Owner, Editor, Viewer per workspace

**Explicitly out of scope for v1:**

| Feature | Reason |
|---|---|
| External connectors (Notion, GDrive, etc.) | Deferred to v2 — Airweave integration adds complexity; file upload validates core loop |
| Cross-workspace global knowledge graph | Deferred to v3 — requires graph federation strategy |
| Podcast / audio generation | Open-notebook feature not relevant to corporate KB use case |
| Public sharing / external access | Security boundary — internal only in v1 |
| Mobile app | Web-first |
| Analytics / usage dashboards | v3 |

---

## Constraints

- **Timeline:** No hard deadline stated — ship v1 milestones iteratively.
- **Technical:** Must run fully self-hosted (Docker Compose) — no data leaves company infrastructure.
- **Resources:** Single team (small), so architectural choices must minimize operational complexity.
- **Base:** Built on top of open-notebook fork — reuse what works, replace what doesn't fit.
