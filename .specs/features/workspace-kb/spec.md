# M1 Feature Specification — Core KB Platform

## Problem Statement

Company knowledge is split across personal ChatGPT/NotebookLM accounts, Notion, SharePoint, Airtable, and individual employee tools. There is no central place where employees or AI agents can query the full body of company knowledge. When employees leave, knowledge leaves with them. This feature establishes the foundational platform that owns that knowledge.

## Goals

- [ ] G1: Authenticated employees can create and manage workspaces, upload documents, and chat with their content — all within company-controlled infrastructure.
- [ ] G2: Each workspace builds a knowledge graph (LightRAG) from ingested content, enabling grounded, cited answers beyond keyword search.
- [ ] G3: AI coding agents (Cursor, Claude, Copilot) can query workspace knowledge via MCP without manual context copying.

## Out of Scope

Explicitly excluded from this spec. Documented to prevent scope creep.

| Feature | Reason |
|---|---|
| External connectors (Notion, GDrive, Airweave) | M2 — validate core loop first |
| Cross-workspace global graph | M3 — requires graph federation design |
| Podcast generation | Not relevant to corporate KB use case |
| Public / external sharing | Security boundary — internal only |
| Analytics dashboard | M4 |
| GitHub connector | M2 |

---

## User Stories

### P1: User Authentication [AUTH] ⭐ MVP

**User Story:** As an employee, I want to log in with my company identity (SSO) or email invitation so that I can access the KB platform without creating a separate account.

**Why P1:** No auth = no multi-user KB. Everything else depends on identity.

**Acceptance Criteria:**

1. WHEN a user visits the platform THEN system SHALL present a Clerk-powered login screen.
2. WHEN an org admin configures SSO (Google/Azure OIDC) THEN system SHALL allow users to sign in with their corporate identity.
3. WHEN a user is invited by email THEN system SHALL send an invite link valid for 72 hours.
4. WHEN a user's account is deactivated by an admin THEN system SHALL revoke access on the next request without requiring a redeploy.
5. WHEN a user logs in THEN system SHALL associate them with their organization and load their workspace membership list.

**Independent Test:** Can demo by logging in via email invite, verifying user appears in admin user list.

---

### P1: Workspace Creation & Management [WS] ⭐ MVP

**User Story:** As an employee, I want to create workspaces (private or shared) and invite colleagues so that I can organize knowledge by project, product, or area.

**Why P1:** Workspaces are the primary organizing unit. Without them the KB is a flat pile of documents.

**Acceptance Criteria:**

1. WHEN a user creates a workspace THEN system SHALL require a name and visibility setting (Private | Shared | Community).
2. WHEN visibility is Private THEN system SHALL only show the workspace to its Owner.
3. WHEN visibility is Shared THEN system SHALL allow the Owner to invite specific users or groups with a role (Editor or Viewer).
4. WHEN visibility is Community THEN system SHALL make the workspace discoverable in the org directory; any org member may request access; Owner approves.
5. WHEN a user is assigned Editor role THEN system SHALL allow them to upload sources and create notes but NOT change workspace settings or delete the workspace.
6. WHEN a user is assigned Viewer role THEN system SHALL allow them to read, search, and chat but NOT upload or edit.
7. WHEN an Owner deletes a workspace THEN system SHALL require confirmation and permanently delete all sources, graph data, and notes associated with it.

**Independent Test:** Can demo by creating three workspaces (one per visibility type), inviting a second user as Editor, verifying they can upload but not delete the workspace.

---

### P1: Document Upload & Ingestion [INGEST] ⭐ MVP

**User Story:** As an Editor, I want to upload PDF, DOCX, TXT, and Markdown files to my workspace so that the system extracts and indexes their content into the knowledge graph.

**Why P1:** No content = no KB. Upload is the only ingestion path in v1.

**Acceptance Criteria:**

1. WHEN a user uploads a supported file (PDF, DOCX, TXT, MD) THEN system SHALL accept the file, queue it for processing, and show a "Processing" status indicator.
2. WHEN processing completes successfully THEN system SHALL show "Ready" status and the source appears in the workspace source list.
3. WHEN processing fails THEN system SHALL show "Failed" status with an error description and allow the user to retry.
4. WHEN a PDF contains tables or images THEN system SHALL extract table content as structured text and run OCR on images via RAGAnything.
5. WHEN a source is deleted by an Editor or Owner THEN system SHALL remove its content, embeddings, and graph nodes from the workspace graph.
6. WHEN a file exceeds 50MB THEN system SHALL reject it with a clear size limit message before upload begins.
7. WHEN the same file is uploaded twice to the same workspace THEN system SHALL warn the user and offer to skip or replace.

**Independent Test:** Can demo by uploading a multi-page PDF with a table, verifying source status reaches "Ready", and confirming the table content is queryable.

---

### P1: Knowledge Graph Construction [GRAPH] ⭐ MVP

**User Story:** As the system, I need to build a per-workspace LightRAG knowledge graph from ingested content so that queries can use graph traversal in addition to vector similarity.

**Why P1:** Graph-based retrieval is the core architectural differentiator. Without it, the platform is just a standard RAG with better UX.

**Acceptance Criteria:**

1. WHEN a source reaches "Ready" status THEN system SHALL trigger LightRAG graph extraction asynchronously (entity + relationship extraction).
2. WHEN graph extraction completes THEN system SHALL update the workspace's graph store with new nodes and edges.
3. WHEN graph extraction fails THEN system SHALL log the error, mark the source with a "Graph Warning" flag, and NOT block the source from vector search.
4. WHEN a source is deleted THEN system SHALL remove its contributed nodes and edges from the workspace graph (cascade delete).
5. WHEN a workspace graph is queried THEN system SHALL use LightRAG hybrid mode (vector + graph + keyword) ranked by combined relevance score.

**Independent Test:** Can demo by uploading a doc with named entities, querying a relationship between two entities, and getting a graph-traversal-informed answer with source citation.

---

### P1: Chat Interface [CHAT] ⭐ MVP

**User Story:** As an employee, I want to ask natural language questions scoped to one or more workspaces and receive grounded, cited answers so that I can get business information without digging through documents.

**Why P1:** Chat is the primary user-facing value. Everything before this is infrastructure.

**Acceptance Criteria:**

1. WHEN a user opens a workspace THEN system SHALL show a chat interface with a workspace scope selector (current workspace or multi-select from accessible workspaces).
2. WHEN a user submits a question THEN system SHALL retrieve context via LightRAG hybrid search and stream the answer back.
3. WHEN an answer is generated THEN system SHALL display source citations (document name + page/section) inline.
4. WHEN no relevant content is found THEN system SHALL respond with "I couldn't find information on this in the selected workspaces" rather than hallucinating.
5. WHEN a user clicks a source citation THEN system SHALL open a preview of the source chunk that informed the answer.
6. WHEN a user saves a chat answer as a note THEN system SHALL create a note in the current workspace with the answer content and source citations preserved.
7. WHEN the chat model is not configured THEN system SHALL show a clear error directing the user to Settings → Models.

**Independent Test:** Can demo by uploading a product spec document, asking a specific business question about it, receiving a cited answer, and saving it as a note.

---

### P1: MCP Server [MCP] ⭐ MVP

**User Story:** As an AI coding agent (Cursor, Claude, Copilot), I want to query workspace knowledge via MCP so that I can retrieve business rules, domain context, and validation constraints without a human copying them into context.

**Why P1:** MCP is the agent-facing output — it's what makes the platform useful beyond human users.

**Acceptance Criteria:**

1. WHEN the platform is running THEN system SHALL expose an MCP-compatible server at a configurable endpoint.
2. WHEN an agent calls `search_kb(query, workspace_ids)` THEN system SHALL return ranked results with content, source name, and confidence score.
3. WHEN an agent calls `list_workspaces()` THEN system SHALL return only workspaces the API key's owner has at least Viewer access to.
4. WHEN an agent calls `get_entity(name, workspace_id)` THEN system SHALL return the entity's description, related entities, and source references from the workspace graph.
5. WHEN an API key is invalid or expired THEN system SHALL return HTTP 401.
6. WHEN a workspace_id in the request is not accessible by the API key owner THEN system SHALL return HTTP 403 for that workspace (not leak its existence).
7. WHEN an admin generates an MCP API key THEN system SHALL scope the key to specific workspaces at creation time.

**Independent Test:** Can demo by configuring the MCP server in Cursor, asking Cursor to "check the business rules for X", and seeing it call `search_kb` and return grounded context.

---

### P2: Note Management [NOTES]

**User Story:** As an employee, I want to create, edit, and organize notes within a workspace so that I can capture processed knowledge and insights, not just raw source documents.

**Why P2:** Notes are a first-class knowledge artifact, but the chat-to-note save path (P1) is the primary creation pattern. A full notes editor is needed but not MVP-blocking.

**Acceptance Criteria:**

1. WHEN a user creates a note THEN system SHALL require a title and accept Markdown body content.
2. WHEN a note is saved THEN system SHALL index it into the workspace's knowledge graph as a source of equal weight to uploaded documents.
3. WHEN a note is edited THEN system SHALL re-index the changed content incrementally.
4. WHEN a user searches the workspace THEN system SHALL surface notes alongside document sources in results.

**Independent Test:** Can demo by creating a note, waiting for indexing, and verifying it appears in search results.

---

### P2: Source Transformations [TRANSFORM]

**User Story:** As an Editor, I want to run AI transformations on a source (summarize, extract key points, identify action items) so that I can quickly generate structured knowledge from raw uploads.

**Why P2:** Inherited from open-notebook — high value but not blocking the core KB loop.

**Acceptance Criteria:**

1. WHEN a source is in "Ready" status THEN system SHALL offer a "Transform" action with available transformation templates.
2. WHEN a transformation runs THEN system SHALL store the output as a note linked to the source.
3. WHEN a transformation fails THEN system SHALL show the error and allow retry.

**Independent Test:** Can demo by running "Summarize" on a PDF, verifying a note is created with the summary and a link back to the source.

---

### P3: Workspace Activity Feed [ACTIVITY]

**User Story:** As a workspace member, I want to see recent activity (new sources, notes, transformations) so that I know what's changed without checking every document.

**Why P3:** Useful for shared/community workspaces but not required for core value delivery.

**Acceptance Criteria:**

1. WHEN a source is uploaded, processed, or deleted THEN system SHALL append an entry to the workspace activity feed.
2. WHEN a note is created or edited THEN system SHALL append an entry to the activity feed.
3. WHEN a user views the workspace THEN system SHALL display the last 50 activity entries in reverse chronological order.

---

## Edge Cases

- WHEN a user uploads a file with no extractable text (scanned PDF, image-only) THEN system SHALL attempt OCR and, if OCR yields < 100 characters, mark the source as "Low Content" with a warning.
- WHEN a user is removed from a workspace THEN system SHALL immediately revoke their chat and search access; their previously created notes are reassigned to the workspace Owner.
- WHEN the LightRAG extraction service is unavailable THEN system SHALL queue the extraction job and retry with exponential backoff up to 5 attempts before marking as "Graph Warning".
- WHEN a user queries multiple workspaces and has Viewer access to some but not others THEN system SHALL silently exclude inaccessible workspaces from results without exposing their names.
- WHEN the SurrealDB graph exceeds workspace storage quota THEN system SHALL warn the workspace Owner before refusing new uploads.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|---|---|---|---|
| AUTH-01 | P1: User Authentication | Design | Pending |
| AUTH-02 | P1: User Authentication | Design | Pending |
| AUTH-03 | P1: User Authentication | Design | Pending |
| AUTH-04 | P1: User Authentication | Design | Pending |
| AUTH-05 | P1: User Authentication | Design | Pending |
| WS-01 | P1: Workspace Management | Design | Pending |
| WS-02 | P1: Workspace Management | Design | Pending |
| WS-03 | P1: Workspace Management | Design | Pending |
| WS-04 | P1: Workspace Management | Design | Pending |
| WS-05 | P1: Workspace Management | Design | Pending |
| WS-06 | P1: Workspace Management | Design | Pending |
| WS-07 | P1: Workspace Management | Design | Pending |
| INGEST-01 | P1: Document Upload | Design | Pending |
| INGEST-02 | P1: Document Upload | Design | Pending |
| INGEST-03 | P1: Document Upload | Design | Pending |
| INGEST-04 | P1: Document Upload | Design | Pending |
| INGEST-05 | P1: Document Upload | Design | Pending |
| INGEST-06 | P1: Document Upload | Design | Pending |
| INGEST-07 | P1: Document Upload | Design | Pending |
| GRAPH-01 | P1: Knowledge Graph | Design | Pending |
| GRAPH-02 | P1: Knowledge Graph | Design | Pending |
| GRAPH-03 | P1: Knowledge Graph | Design | Pending |
| GRAPH-04 | P1: Knowledge Graph | Design | Pending |
| GRAPH-05 | P1: Knowledge Graph | Design | Pending |
| CHAT-01 | P1: Chat Interface | Design | Pending |
| CHAT-02 | P1: Chat Interface | Design | Pending |
| CHAT-03 | P1: Chat Interface | Design | Pending |
| CHAT-04 | P1: Chat Interface | Design | Pending |
| CHAT-05 | P1: Chat Interface | Design | Pending |
| CHAT-06 | P1: Chat Interface | Design | Pending |
| CHAT-07 | P1: Chat Interface | Design | Pending |
| MCP-01 | P1: MCP Server | Design | Pending |
| MCP-02 | P1: MCP Server | Design | Pending |
| MCP-03 | P1: MCP Server | Design | Pending |
| MCP-04 | P1: MCP Server | Design | Pending |
| MCP-05 | P1: MCP Server | Design | Pending |
| MCP-06 | P1: MCP Server | Design | Pending |
| MCP-07 | P1: MCP Server | Design | Pending |
| NOTES-01 | P2: Note Management | — | Pending |
| NOTES-02 | P2: Note Management | — | Pending |
| NOTES-03 | P2: Note Management | — | Pending |
| NOTES-04 | P2: Note Management | — | Pending |
| TRANSFORM-01 | P2: Source Transformations | — | Pending |
| TRANSFORM-02 | P2: Source Transformations | — | Pending |
| TRANSFORM-03 | P2: Source Transformations | — | Pending |
| ACTIVITY-01 | P3: Activity Feed | — | Pending |
| ACTIVITY-02 | P3: Activity Feed | — | Pending |
| ACTIVITY-03 | P3: Activity Feed | — | Pending |

**Coverage:** 47 total, 0 mapped to tasks, 47 unmapped ⚠️

---

## Success Criteria

- [ ] An employee can log in, create a workspace, upload a PDF, and get a cited answer from it in under 5 minutes.
- [ ] A workspace's knowledge graph is isolated — querying Workspace A never returns content from Workspace B.
- [ ] An AI coding agent configured with the MCP endpoint can retrieve a business rule from the KB in a single tool call.
- [ ] Deleting a source removes it from both vector search and graph traversal — no ghost results.
- [ ] A Community workspace is visible in the org directory to all members but its content is only accessible to granted members.
