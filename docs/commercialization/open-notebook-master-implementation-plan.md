# Open Notebook → Commercial White-Label SaaS
## Master Implementation Plan (structured for Claude Code execution)

**Base project:** `lfnovo/open-notebook` v1.10.0 (MIT)
**Goal:** Turn the fork into a commercial, white-labelable, multi-client SaaS with enterprise auth, external content sources, cross-platform packaging, and onboarding.
**Audience:** Claude Code (executor) + engineering lead (reviewer)
**Status of Phase 0:** COMPLETE (licensing due diligence done — see the R&D dossier). This document covers Phases 1–8.

---

# PART A — How to use this document (execution protocol)

**This is a program, not a task. Do NOT execute all work packages at once.** Run them one at a time, in the order given in Part C, each on its own branch, each verified against its acceptance criteria before the next begins.

**Rules for Claude Code (apply to every work package):**

1. **Read before writing.** This repo already contains `CLAUDE.md` files in most directories (`api/`, `open_notebook/`, `open_notebook/graphs/`, `frontend/src/lib/`, etc.). Read the relevant `CLAUDE.md` before touching any directory, and **update it** when you change how that directory works.
2. **One branch per work package.** Name it `wp-<n>-<slug>` (e.g. `wp-2-entra-auth`). Never mix two work packages in one branch.
3. **Tests are mandatory.** No work package is "done" until its acceptance criteria pass AND tests are green. If the area has no tests, write characterization tests FIRST (see WP0).
4. **Verify, then stop.** At the end of each work package, run the acceptance checks, report pass/fail against each criterion, and STOP for human review. Do not roll into the next package.
5. **Never fabricate numbers or behavior.** For anything requiring measurement (WP6), run the benchmark harness and report real output. If something can't be determined, say so.
6. **Preserve upstream mergeability.** Prefer adding new modules/adapters over rewriting core files, so future upstream fixes still merge.

**The safety framework (Phases 1–8) maps onto the work packages below.** WP0 is Phases 1–3 (fork hygiene, baseline, test net). Everything after is feature work built on that foundation.

---

# PART B — Current architecture (ground truth)

*This is verified from the v1.10.0 source. Trust it as the starting map; confirm with a fresh read before editing.*

### Backend (Python, FastAPI) — ~20k LOC, 87 files
- **API layer:** `api/` with 22 routers in `api/routers/`: `auth, chat, commands, config, context, credentials, embedding, embedding_rebuild, episode_profiles, insights, languages, models, notebooks, notes, podcasts, search, settings, source_chat, sources, speaker_profiles, transformations`.
- **Domain models:** `open_notebook/domain/`: `base` (ORM base `ObjectModel`), `notebook`, `credential`, `content_settings`, `provider_config`, `transformation`.
- **AI orchestration:** `open_notebook/graphs/` (LangGraph): `ask, chat, prompt, source, source_chat, tools, transformation`.
- **Data access:** `open_notebook/database/repository.py` (thin SurrealQL wrapper, 207 lines) + 15 `.surrealql` migrations.
- **Background jobs:** `surreal-commands` + `commands/` (`source_commands`, `embedding_commands`, `podcast_commands`).
- **AI provider abstraction:** `esperanto` + `langchain-*`.
- **Content ingestion:** `content-core` (PDF, web, audio via STT, YouTube, Office).

### Frontend (Next.js App Router, TypeScript) — `frontend/src/`
- **Routes:** route groups `(auth)/login/` and `(dashboard)/{notebooks,sources,search,podcasts,transformations,settings,advanced}`.
- **Components:** domain-organized under `components/`: `ui/` (shadcn), `auth/`, `layout/` (incl. `AppSidebar.tsx`), `notebooks/`, `sources/`, `search/`, `podcasts/`, `settings/`, `providers/`, `common/`, `errors/`.
- **State/data:** `lib/stores/` (zustand, incl. `auth-store.ts`), `lib/hooks/` (incl. `use-auth.ts`), `lib/api/` (axios client), `lib/types/` (incl. `auth.ts`).
- **Theming:** `next-themes` + Tailwind + shadcn CSS variables in `app/globals.css`. App title hardcoded in `app/layout.tsx`; logo referenced as `/logo.svg` in `AppSidebar.tsx`.
- **i18n:** `react-i18next` with 15 locales in `lib/locales/`.
- **Tests:** Vitest configured (`vitest.config.ts`).

### Auth (CRITICAL — the program pivot)
- Backend: `api/auth.py` → `PasswordAuthMiddleware`. **A single shared password** (`OPEN_NOTEBOOK_PASSWORD`) sent as `Bearer <password>`. If unset, auth is effectively open.
- **There is NO user model, NO per-user data, NO multi-tenancy.** All data is global to the instance.
- Frontend: `LoginForm.tsx`, `auth-store.ts`, `use-auth.ts`, `types/auth.ts` exist to build on.

### Deployment
- `Dockerfile`, `Dockerfile.single` (all-in-one), `docker-compose.yml`. Config via env vars (`SURREAL_URL`, `OPEN_NOTEBOOK_PASSWORD`, `OPEN_NOTEBOOK_ENCRYPTION_KEY`, provider keys).

---

# PART C — Execution order & dependency graph

**Do them in this order. The arrows are hard dependencies.**

```
WP0 Foundations (fork hygiene, baseline, test net, CI)
     │
     ▼
WP1 Licensing & compliance ── (independent, can run in parallel with WP0)
     │
     ▼
WP-DEC  MULTI-TENANCY DECISION  ◄── the fork in the road; a human decision, not code
     │
     ▼
WP2 Identity & Entra ID auth  ──► unlocks per-user/per-client everything
     │
     ├──► WP3 Frontend map + white-label theming (needs tenant model for per-client themes)
     ├──► WP5 External source connectors (needs per-user OAuth token storage)
     │
WP4 Backend/API documentation ── (can run early; pure documentation, low risk)
WP6 Doc-processing benchmarks ── (can run after WP0; needs target hardware)
WP7 Cross-platform packaging ── (after WP2/WP3 so installer ships the real app)
WP8 Onboarding + tooltips ────── (LAST; needs final flows to guide users through)
```

**Why WP2 (auth) gates so much:** white-label-per-client and per-user SharePoint tokens both need to know "who is this user and which client/tenant do they belong to." Building those before identity means building them twice.

---

# PART D — Work packages

Each work package is written so you can hand it to Claude Code as a self-contained assignment.

---

## WP0 — Foundations (Phases 1–3)

**Objective:** Establish a known-good, test-guarded, CI-enforced baseline of the fork before any feature work.

**Tasks:**
1. Fork hygiene: confirm `origin` = our private repo, add `upstream` = `lfnovo/open-notebook`, tag the fork point `git tag upstream-base`.
2. Reproduce a clean build in a container: backend (`uv`/pip), SurrealDB, frontend (`npm build`). Document exact steps in `/docs/DEV_SETUP.md`.
3. Establish the test net: confirm Vitest (frontend) runs; add `pytest` for backend if absent. Write **characterization tests** for the critical paths — source ingestion, search (text + vector), chat, and one full notebook CRUD cycle — capturing current behavior as the regression baseline.
4. Add a coverage tool and set a ratchet (coverage may only increase).
5. Set up CI (GitHub Actions): on every PR run lint → typecheck → backend tests → frontend tests → build. Add branch protection: no merge on red.
6. Add license scanning to CI: `pip-licenses` (Python) + `license-checker` (frontend), failing on any GPL/AGPL that appears via a future dependency update.

**Acceptance criteria:**
- [ ] Clean build reproducible from `/docs/DEV_SETUP.md` on a fresh machine.
- [ ] `upstream-base` tag exists; `upstream` remote configured.
- [ ] Characterization tests exist and pass for ingestion, search, chat, notebook CRUD.
- [ ] CI runs on PR and blocks merge on failure.
- [ ] License scan runs in CI and passes.

---

## WP1 — Licensing & compliance (end-to-end)

**Objective:** Make the fork fully compliant to ship commercially, forever, with automated drift protection.

**Current-state facts (from Phase 0):** core + almost all deps are MIT/BSD/Apache. `pycountry` is LGPL-2.1 (safe if unmodified). SurrealDB is BSL 1.1 — **decision resolved: keep it; commercial embedded use is free and permitted; no license purchase required.** Enterprise license only needed for advanced compliance features or DBaaS resale (not our model).

**Tasks (in order):**
1. **Preserve original attribution.** Keep the upstream MIT `LICENSE` and Luis Novo's copyright. Add our own copyright line in a new top block — never replace his. Do the same for the MIT sub-packages if we vendor any of them.
2. **Generate `THIRD-PARTY-NOTICES.md`** at repo root: enumerate every dependency (Python + frontend) with name, version, license, and copyright. Auto-generate it via `pip-licenses --format=markdown` and `license-checker --production`, then hand-add SurrealDB's BSL 1.1 entry (source-available; converts to Apache 2.0 four years after each release; commercial embedding permitted; DBaaS resale prohibited without enterprise license).
3. **Do NOT modify `pycountry` source.** Add a lint/CI note asserting it stays an unmodified dependency (keeps LGPL obligation at zero).
4. **Rebrand assets** (coordinate with WP3): replace name "Open Notebook", `/logo.svg`, and `app/layout.tsx` title with our brand. Remove upstream brand assets from shipped artifacts.
5. **Bundle-check for SurrealDB:** in the stock setup we pull the official `surrealdb/surrealdb` image separately (dependency, not redistribution — cleanest). IF we build our own image that bundles the SurrealDB binary, include the BSL license text inside that image. Document which path we chose.
6. **AI provider terms:** create `/docs/PROVIDER_TERMS.md` listing every enabled provider (OpenAI, Anthropic, Google, Groq, Mistral, DeepSeek, Ollama, plus any TTS/STT) and a link to its commercial ToS; flag any that restrict commercial resale so legal can review.
7. **Encryption key management:** ensure `OPEN_NOTEBOOK_ENCRYPTION_KEY` is generated per-deployment and never committed; document rotation.
8. **Keep the CI license scan from WP0** as the ongoing drift guard.

**Acceptance criteria:**
- [ ] `LICENSE` retains upstream copyright + our added copyright.
- [ ] `THIRD-PARTY-NOTICES.md` complete and generated reproducibly.
- [ ] SurrealDB BSL entry present and accurate.
- [ ] `pycountry` documented as unmodified; CI asserts it.
- [ ] `/docs/PROVIDER_TERMS.md` exists.
- [ ] No secrets/keys committed; encryption key handling documented.

---

## WP-DEC — Multi-tenancy decision (HUMAN DECISION, blocks WP2/3/5)

**This is not code. Engineering + leadership must choose ONE model before WP2:**

- **Model A — Single-tenant per client (simplest):** each client gets their own isolated instance (own DB, own deployment, own branding). No cross-client data separation needed inside the app. Easiest to build; higher ops cost per client. Fits the "install per client" mindset and pairs naturally with WP7's installer.
- **Model B — Multi-tenant (one instance, many clients):** one deployment serves all clients; every row is tagged with a `tenant_id`; strict data isolation enforced in every query. Lower ops cost; far more engineering (row-level isolation, tenant context in all 121 query sites, per-tenant theming at runtime). Higher security burden.

**Recommendation for a first commercial release:** **Model A (single-tenant per client).** It lets you ship faster, keeps data isolation trivial (physical separation), and matches white-label-per-client + per-client installer cleanly. Move to Model B later only if per-client ops cost becomes the bottleneck. **Document the choice in `/docs/TENANCY.md`; the rest of the plan assumes Model A unless changed.**

---

## WP2 — Identity & Microsoft Entra ID authentication

**Objective:** Replace the single shared password with real per-user identity via Entra ID (Azure AD) using industry-standard OIDC, with a pluggable design so SAML/other SSO can be added later.

**Current state:** `PasswordAuthMiddleware` (single password). Frontend `auth-store`/`use-auth`/`LoginForm` exist. No user model.

**Design (industry standard — OIDC Authorization Code + PKCE):**
- Use **Entra ID as an OpenID Connect provider**. The web app performs Authorization Code flow with PKCE; the backend validates JWT access tokens (issuer, audience, signature via Entra's JWKS, expiry) on every request.
- Introduce a minimal **`user` model** (id, email, display name, entra `oid`/`sub`, tenant/client id, role). Provision users on first successful login (just-in-time).
- Keep an **abstraction layer** (`AuthProvider` interface) so `EntraOIDCProvider` is one implementation and `SamlProvider` / `GenericOIDCProvider` can be added without touching call sites.

**Tasks:**
1. **Backend auth abstraction:** create `api/auth/` package with an `AuthProvider` protocol and move the existing password logic into `PasswordAuthProvider` (keep as a dev/local fallback behind a config flag).
2. **Entra OIDC provider:** implement `EntraOIDCProvider` — token validation against Entra JWKS, issuer/audience checks, role/claims extraction. Use a maintained library (e.g. `msal` for app-side flows and standard JWT validation for API-side). Config via env: `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_REDIRECT_URI`, `AUTH_PROVIDER=entra`.
3. **Replace middleware:** swap `PasswordAuthMiddleware` for an `AuthMiddleware` that delegates to the configured provider and attaches the resolved `user` (and `tenant/client id`) to the request context.
4. **User model + JIT provisioning:** add the `user` table/model + migration; create-or-update user on first valid login.
5. **Authorization:** define roles (at least `admin`, `user`); enforce on sensitive routes (settings, models, credentials, embedding rebuild).
6. **Data ownership:** associate notebooks/sources with a `user_id` (and `client_id` under Model A this is mostly the instance owner; keep the column for future Model B). Update create/read paths so users see their own data.
7. **Frontend:** implement the Entra login redirect flow in `LoginForm`/`auth-store`; store tokens securely (httpOnly cookie preferred over localStorage); silent refresh; logout that clears the Entra session; guard `(dashboard)` routes.
8. **Session & token handling:** refresh tokens, expiry handling, 401 → re-auth, CSRF protection on cookie-based flows.
9. **Docs:** `/docs/AUTH.md` — how to register the app in Entra (redirect URIs, API permissions, admin consent), env config, and how to add another provider.

**Optional extension (SAML / other SSO):** because of the `AuthProvider` abstraction, add `SamlProvider` (e.g. via `python3-saml`) and/or a generic OIDC provider (Okta, Google Workspace, Auth0) later. Document the SAML app registration and assertion mapping in `/docs/AUTH.md`. Same user model; only the provider differs.

**Acceptance criteria:**
- [ ] Login via a real Entra account works end-to-end (redirect → callback → session).
- [ ] Every API request validates a real Entra-issued token (issuer/audience/signature/expiry).
- [ ] Users are JIT-provisioned; a `user` record exists after first login.
- [ ] Roles enforced on sensitive routes (unauthorized returns 403).
- [ ] Users only see their own notebooks/sources.
- [ ] Password provider still works as a local-dev fallback behind a flag.
- [ ] Adding a second provider requires no change to route handlers (proven by a stub `GenericOIDCProvider`).
- [ ] `/docs/AUTH.md` complete.

---

## WP3 — Frontend architecture map + white-label theming

**Objective:** (a) Produce a complete map of the frontend so any future change is "we know exactly where"; (b) build a **config-driven white-label system** so a new client's theme, logo, colors, and app name require **zero code changes** — only config.

### Part 3a — Architecture map (deliverable: `/docs/FRONTEND_MAP.md`)
Document, from the real code:
- **Route → page → component tree** for each `(dashboard)` route (notebooks, sources, search, podcasts, transformations, settings, advanced) and `(auth)/login`.
- **Data flow per page:** which zustand store, which `lib/hooks`, which `lib/api` calls, which backend endpoints each screen hits.
- **Shared layout:** `AppSidebar.tsx`, providers, error boundaries.
- **Component catalog:** what each folder under `components/` owns and when to reuse vs. create.
- A **"where do I change X?" table** (e.g. "add a nav item → `AppSidebar.tsx`", "add a settings field → `components/settings/` + `settings` router").

### Part 3b — White-label theming system
**Current state:** shadcn CSS variables in `app/globals.css`; `next-themes`; title hardcoded; logo is a static `/logo.svg`; nav uses i18n.

**Design — a single `BrandConfig` that drives everything:**
1. Define a `BrandConfig` schema: `appName`, `logoUrl` (light/dark), `faviconUrl`, primary/secondary/accent colors, font, support URL, optional custom CSS-variable overrides.
2. **Source of brand config** (Model A): load per-deployment from an env-referenced JSON/YAML (`BRAND_CONFIG_PATH`) or a `/config/brand` backend endpoint, resolved at app startup. (Under Model B later: resolve per-tenant at request time.)
3. **Apply theme at runtime:** map `BrandConfig` colors → CSS variables injected into `:root` (and dark variants), so no recompile is needed to re-theme. Replace hardcoded title in `layout.tsx` with `brandConfig.appName`; replace `/logo.svg` references (e.g. in `AppSidebar.tsx`) with `brandConfig.logoUrl`.
4. **Assets:** support per-client logo/favicon via a configurable asset path or upload, not a committed file.
5. **Provide a `themes/` folder of ready presets** + a documented "add a new client theme" procedure (drop a config + assets; no build).
6. **Optional admin UI:** a settings screen (admin-only, ties to WP2 roles) to edit `BrandConfig` live.

**Acceptance criteria:**
- [ ] `/docs/FRONTEND_MAP.md` covers every route with its component tree, data flow, and backend calls, plus the "where do I change X?" table.
- [ ] A new client can be branded (name, logo, favicon, colors) **by config only, no code edit, no rebuild** — demonstrated by shipping two visibly different brands from the same build.
- [ ] All previously hardcoded brand strings/assets now read from `BrandConfig`.
- [ ] Dark/light both themed correctly.

---

## WP4 — Backend & API architecture documentation

**Objective:** A complete, precise map of the backend so any change/addition is "we know exactly where and how." (Documentation package — low risk, high leverage; can run early.)

**Deliverable: `/docs/BACKEND_MAP.md` containing:**
1. **Router catalog:** all 22 routers, each endpoint (method, path, request/response model, auth requirement), and the domain/service it calls.
2. **Domain model catalog:** `ObjectModel` base pattern; each model's fields, relationships (the graph edges `reference`/`refers_to`/`artifact`), and lifecycle.
3. **AI orchestration map:** each LangGraph in `graphs/` (`ask, chat, source, source_chat, transformation`) — inputs, steps, models used, outputs.
4. **Data layer:** how `repository.py` works, the 121 call-site pattern, the 15 migrations, and the SurrealDB features in use (analyzer, BM25 indexes, vector search, events/triggers).
5. **Background jobs:** how `surreal-commands` submits/tracks jobs; the four command modules; how to add a new job.
6. **Config & secrets:** every env var, what it controls, and the credential-encryption flow.
7. **"How do I add X?" playbooks:** add an endpoint, add a domain model + migration, add a provider, add a background job, add a source type.

**Acceptance criteria:**
- [ ] Every router and endpoint documented with auth + models.
- [ ] Every domain model and graph documented.
- [ ] The five "how do I add X?" playbooks present and accurate.
- [ ] A new engineer can locate where to make a given change using only this doc.

---

## WP5 — External source connectors (SharePoint / DMS / bulk links)

**Objective:** Let users add a **source location** (SharePoint site/folder, DMS folder/ID, or a link that yields many documents) and have the app pull *all* documents from it and make them chat-able — instead of uploading one file at a time.

**Current state:** `api/routers/sources.py` handles single `UploadFile` / URL / text via `save_uploaded_file` → `content-core` extraction → `graphs/source.py` → `source_commands` job. This is the seam.

**Design — a pluggable `SourceConnector` abstraction:**
1. Define a `SourceConnector` interface: `authenticate()`, `list_documents(location)`, `fetch_document(ref)`. Each connector yields a normalized document stream that feeds the **existing** ingestion pipeline (reuse `content-core` + `graphs/source.py`; don't reinvent extraction).
2. **SharePoint connector (industry standard):** use **Microsoft Graph API** with OAuth2 on behalf of the signed-in Entra user (this is why WP2 comes first — per-user tokens/consent). Scopes like `Sites.Read.All`/`Files.Read.All` (least privilege; admin consent documented). Given a site/drive/folder, enumerate items, download supported files, stream them into ingestion.
3. **Generic DMS / multi-doc link connector:** given a folder URL or an ID that resolves to many documents, enumerate and fetch. Provide a base implementation others can extend.
4. **Bulk ingestion job:** extend `commands/source_commands.py` so one "add source location" action fans out into N document-ingestion jobs, with per-document progress and partial-failure handling (one bad file doesn't fail the batch).
5. **Chat over the set:** ensure the batch is grouped (e.g. under one notebook/source-group) so the user can chat across all pulled documents using the existing vector/text search + chat graph.
6. **Frontend:** add a "Add from SharePoint / Link" flow in `components/sources/steps/` with connection, folder picker, selection, and progress UI.
7. **Security:** store connector OAuth tokens encrypted (reuse the encryption-key infra), per user; respect source-system permissions (never fetch what the user can't access).
8. **Docs:** `/docs/CONNECTORS.md` — how to register the SharePoint app in Entra, scopes/consent, and how to add a new connector.

**Acceptance criteria:**
- [ ] A user can connect SharePoint, pick a folder, and pull all supported docs in one action.
- [ ] Ingestion reuses the existing pipeline (no duplicate extraction logic).
- [ ] Batch shows per-document progress; a single failure doesn't abort the batch.
- [ ] User can chat across the whole pulled set.
- [ ] Tokens stored encrypted, per user; source-system permissions respected.
- [ ] Adding a new connector requires implementing only the `SourceConnector` interface.
- [ ] `/docs/CONNECTORS.md` complete.

---

## WP6 — Document processing: limits, types, performance & hardware sizing (MEASURED, not guessed)

**Objective:** Produce **real, defensible numbers** for: max document size, processing time, accuracy, supported types, and the hardware needed — so you can tell clients the truth.

**⚠️ These numbers must be measured on target hardware, not asserted. This work package builds the harness and runs it.**

**Tasks:**
1. **Enumerate supported types** from `content-core`'s real capabilities (PDF, DOCX/Office, HTML/web, plain text, YouTube, audio via STT, etc.). Document what's supported today and what would need work to add (e.g. scanned-image OCR, EPUB).
2. **Build a benchmark harness** (`/benchmarks/`) that ingests a fixed corpus of documents of varying size/type and records, per document: ingestion time, extraction success, embedding time, memory peak, and search/chat latency. Make it repeatable and parameterized by hardware.
3. **Assemble a representative corpus:** small (1–5 pp), medium (20–50 pp), large (200–500 pp), very large (1000+ pp), plus a scanned PDF, an audio file, and a web page — so limits are found empirically (where does it slow down / fail / run out of memory).
4. **Accuracy methodology:** define how accuracy is measured (extraction fidelity vs. source; retrieval relevance via a labeled Q&A set; chat groundedness). Report accuracy as a method + numbers, not a vibe. Note that extraction/answer accuracy depends heavily on the chosen AI/embedding models — report per model tier.
5. **Run on ≥2 hardware profiles** and record real numbers:
   - **Bare-minimum profile** (define target, e.g. 4 vCPU / 16 GB RAM / no GPU) — establish what actually works and how slowly.
   - **Recommended profile** (e.g. 8–16 vCPU / 32–64 GB RAM, GPU if using local models) — establish comfortable production numbers.
   - Note that **local models (Ollama) need far more RAM/GPU** than API-based providers; if using OpenAI/Anthropic APIs, the box mainly needs CPU/RAM for extraction + SurrealDB, not GPU.
6. **Produce `/docs/PERFORMANCE_AND_SIZING.md`:** a client-facing table — supported types, tested size limits, processing time per size/type per hardware profile, accuracy per model tier, and minimum vs. recommended hardware with real figures from the harness.
7. **Extend type support (optional):** if scanned-PDF OCR or additional formats are needed, add them via `content-core` config or an OCR step (e.g. Tesseract) and re-benchmark.

**Acceptance criteria:**
- [ ] Benchmark harness runs repeatably and outputs a metrics report.
- [ ] `/docs/PERFORMANCE_AND_SIZING.md` contains **real measured numbers** for both hardware profiles, not estimates.
- [ ] Supported document types documented with tested size limits and failure points.
- [ ] Accuracy methodology defined and results reported per model tier.
- [ ] Minimum and recommended hardware stated with the numbers that justify them.

---

## WP7 — Cross-platform packaging (Windows + Linux) & installer CLI

**Objective:** The app installs and runs correctly on both Windows and Linux servers, with a helper CLI so a non-expert can stand up an instance for a client.

**Current state:** `Dockerfile`, `Dockerfile.single`, `docker-compose.yml`. Python + Node + SurrealDB.

**Design:**
1. **Primary path — containers (works identically on both OSes):** ensure `docker-compose.yml` (and `Dockerfile.single`) build and run cleanly on Windows (Docker Desktop/WSL2) and Linux. This is the most reliable cross-platform story; document it as the recommended deployment.
2. **Native paths (where containers aren't wanted):**
   - **Linux:** systemd service units + an install script; document dependency install (Python, SurrealDB binary, Node build) for common distros.
   - **Windows:** run as a Windows Service (e.g. via NSSM or a service wrapper); document SurrealDB-on-Windows and the frontend build/serve.
3. **Installer helper CLI** (`onboard`/`install` CLI, Python): interactive setup that (a) checks prerequisites, (b) collects config (brand config path, Entra creds, provider keys, DB settings, encryption key generation), (c) writes the env/config files, (d) initializes the database + runs migrations, (e) starts services, (f) runs a health check and prints the URL. Provide a non-interactive mode (config file / flags) for scripted/repeatable client installs — this is the "don't rebuild per client" deployment counterpart to WP3's per-client theming.
4. **Health & smoke checks:** the CLI verifies DB connectivity, that migrations ran, that the API answers `/health`, and that auth is configured, before declaring success.
5. **Docs:** `/docs/DEPLOYMENT.md` — container path (recommended) + native Windows + native Linux, plus the installer CLI usage for both interactive and scripted installs.

**Acceptance criteria:**
- [ ] Container deployment verified working on both Windows and Linux.
- [ ] Native install documented and verified on at least one Linux distro and Windows Server.
- [ ] Installer CLI performs a full install (prereqs → config → DB init → start → health check) in both interactive and non-interactive modes.
- [ ] A scripted install can stand up a new branded client instance end-to-end.
- [ ] `/docs/DEPLOYMENT.md` complete.

---

## WP8 — Onboarding flow & in-app help (LAST)

**Objective:** First-run onboarding that gets a user set up and productive, plus contextual help tooltips throughout. Built last so it guides users through the *final* flows.

**Tasks:**
1. **First-run/admin setup wizard:** guided steps for a fresh instance — configure AI providers/keys, choose models, (if admin) brand config, connect a source, create the first notebook. Detect "fresh instance" state and launch automatically.
2. **User onboarding tour:** a short guided tour of the core loop (add source → search → chat → transform → podcast) using the real UI, using an accessible tour pattern (spotlight + steps), dismissible and resumable.
3. **Contextual help tooltips:** add `ui/tooltip` (already available via Radix) hints on non-obvious controls across notebooks, sources, search, transformations, podcasts, settings. Keep copy in the **i18n system** (all 15 locales) — never hardcode strings.
4. **Help surface:** a persistent help entry point (docs links, shortcuts, "restart tour", support URL from `BrandConfig`).
5. **Empty states:** every main screen gets a helpful empty state that tells a new user what to do next.
6. **Docs:** `/docs/ONBOARDING.md` — how the wizard/tour/tooltips are structured and how to add/edit steps and copy.

**Acceptance criteria:**
- [ ] Fresh instance launches the setup wizard; completing it leaves a working, configured app.
- [ ] A new user can complete the guided tour of the core loop.
- [ ] Contextual tooltips present on key controls; all copy in i18n (translatable).
- [ ] Every main screen has a useful empty state.
- [ ] Tour is dismissible/resumable; help surface reachable everywhere.
- [ ] `/docs/ONBOARDING.md` complete.

---

# PART E — Definition of done (program level)

The program is complete when:
- All work packages pass their acceptance criteria and CI is green.
- A **new client instance** can be stood up **by config + installer only** — branded (WP3), authenticated via Entra (WP2), with SharePoint sources (WP5), on Windows or Linux (WP7), with onboarding (WP8) — **without writing or rebuilding code per client**.
- Licensing is compliant and drift-guarded (WP1).
- Real performance/sizing numbers exist for client conversations (WP6).
- Backend and frontend are fully mapped (WP3a, WP4) so future changes are locatable.

---

# PART F — Notes, risks & honesty flags

- **WP-DEC is a real decision, not a formality.** Everything downstream assumes Model A (single-tenant per client). If leadership wants Model B (multi-tenant), WP2/3/5 grow substantially (row-level isolation across all 121 query sites) — re-scope before starting WP2.
- **Auth is the biggest single change.** Going from one shared password to real identity touches the backend middleware, a new user model + migration, data ownership, and the whole frontend auth flow. Budget accordingly; do it carefully; it gates the most.
- **WP6 numbers must be measured.** Do not let anyone ship client-facing performance claims that weren't produced by the harness on real hardware.
- **Keep upstream mergeable.** Favor adapters/new modules over rewriting core files, so `git fetch upstream` + selective merge stays possible.
- **This plan is an engineering blueprint, not legal advice.** The licensing package (WP1) should still get a final legal sign-off, especially the SurrealDB BSL position.

*Feed this to Claude Code one work package at a time, in Part C order, verifying acceptance criteria before advancing.*
