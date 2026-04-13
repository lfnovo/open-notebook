# Roadmap

**Current Milestone:** M1 — Foundation
**Status:** Planning

---

## M1 — Foundation: Authenticated Workspaces + File Ingestion

**Goal:** A working KB platform where employees can log in, create workspaces, upload documents, and get AI-grounded answers. This milestone proves the core loop: ingest → graph → query → answer.

**Target:** MVP — first internal deployment

### Features

**Auth & Identity** — PLANNED

- Clerk integration (SSO/OIDC + email invite)
- Organization model: users belong to an org
- Roles: Owner, Editor, Viewer (per workspace)

**Workspace Management** — PLANNED

- Create / rename / delete workspaces
- Visibility: Private (owner only) | Shared (invite-based) | Community (org-wide discoverable)
- Community workspaces: owned by a group/team, no personal ownership
- Workspace membership: invite users or groups

**Document Ingestion** — PLANNED

- Upload: PDF, TXT, DOCX, MD
- RAGAnything pipeline: extract text, tables, images (OCR)
- Async processing queue with status indicator
- Source management: list, delete, re-process

**Knowledge Graph per Workspace** — PLANNED

- LightRAG graph construction on ingested content
- Entity extraction, relationship mapping, concept linking
- Isolated graph per workspace (no cross-workspace leakage)

**Hybrid Search & Chat** — PLANNED

- Query interface: single workspace or multi-workspace selection
- Retrieval: vector similarity + graph traversal + keyword (LightRAG hybrid mode)
- Chat: ask questions, get grounded answers with source citations
- Note saving from chat answers

**MCP Server** — PLANNED

- Expose workspace(s) as MCP tool
- Tools: `search_kb(query, workspace_ids)`, `get_entity(name, workspace_id)`, `list_workspaces()`
- API key auth for agent access
- Per-workspace permission check on every query

---

## M2 — Connectors: Sync External Sources

**Goal:** Users can connect external tools and keep the KB current without manual uploads. The connector layer (Airweave) handles auth, sync scheduling, and change detection.

### Features

**Airweave Connector Integration** — PLANNED

- Embed Airweave as a sidecar service (self-hosted)
- Connector UI: connect, configure, trigger sync, view sync status
- v2 priority connectors: Google Drive, Notion, SharePoint/OneDrive, Airtable
- GitHub connector: ingest READMEs, docs/, inline code comments, ADRs — business knowledge only (no raw code indexing)
- Sync schedule: manual, daily, weekly
- Conflict handling: new version supersedes old, keep version history

**Connector Permissions** — PLANNED

- Connector credentials stored encrypted (Fernet, same as open-notebook pattern)
- Connector scoped to a workspace — content lands in that workspace's graph
- Audit log: what was synced, when, by whom

---

## M3 — Knowledge Graph Federation + Cross-Workspace Discovery

**Goal:** Answers that span multiple workspaces. A product manager can ask a question and get context pulled from the product spec workspace, the engineering workspace, and the regulatory workspace simultaneously.

### Features

**Global Graph Layer** — PLANNED

- Cross-workspace entity resolution (same concept, multiple workspaces)
- Federated query: rank and merge results across workspace graphs
- Permission-aware: user only sees content from workspaces they have access to

**Discovery & Recommendation** — PLANNED

- Community workspace directory: browse and request access
- "Related content" surface: when reading a note, show related entities from other workspaces the user can see
- Trending topics per workspace

---

## M4 — Analytics, Quality & Admin

**Goal:** Operators can measure KB health, identify gaps, and govern content quality.

### Features

**KB Health Dashboard** — PLANNED

- Coverage: which topics have good vs. sparse coverage
- Query analytics: most asked questions, unanswered queries
- Staleness alerts: sources not updated in N days

**Content Governance** — PLANNED

- Content approval workflow for community workspaces
- Version history for notes and sources
- Archiving policy

---

## Future Considerations

- Structured data connectors (SQL databases, BI tools) — query structured data as KB facts
- Regulatory/compliance tagging — classify content by sensitivity or regulatory scope
- External stakeholder access — controlled sharing with partners or auditors
- Fine-tuning pipeline — use curated KB content to fine-tune internal models
- Native Slack/Teams bot — query KB from chat tools
