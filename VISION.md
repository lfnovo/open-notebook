# Open Notebook — Vision & Principles

This document is the product's source of truth in two layers with different lifespans:
**Identity** (durable — what Open Notebook is and refuses to be) and **Current Posture**
(temporal — where we are in the journey and what's on the horizon). Triage and design decisions
are evaluated against this document; the reasoning behind each rule lives in the
[decision records](docs/7-DEVELOPMENT/decisions/README.md).

---

## Identity

Open Notebook is a **privacy-focused, self-hosted alternative to Google's Notebook LM** that
empowers users to:

1. **Own their research data** — full control over where data lives and who can access it
2. **Choose their AI providers** — any provider, or fully local models
3. **Customize their workflows** — adapt the tool to different research needs
4. **Access their work anywhere** — web UI, API, or integrations

### What Open Notebook IS

- A **research assistant** for managing and understanding content
- A **platform** that connects various AI providers
- A **privacy-first** tool that keeps your data under your control
- An **extensible system** with APIs and customization options

### What Open Notebook IS NOT

- A document editor (use Google Docs, Notion, etc.)
- A file storage system (use Dropbox, S3, etc.)
- A general-purpose chatbot (use ChatGPT, Claude, etc.)
- A replacement for your entire workflow (it's one tool in your toolkit)

### Principles

Durable, normative rules. Each links to the decision record that established it.

| Principle | Rule |
|---|---|
| **Privacy first** | User data stays under user control by default. Self-hosted is the primary use case; no telemetry without opt-in; no hard dependency on specific cloud services. |
| **Provider-agnostic core** | The default is portable: features must work across the provider matrix. Adopting a provider-exclusive capability is allowed but is a deliberate decision that requires a [PDR](docs/7-DEVELOPMENT/decisions/README.md) ([PDR-002](docs/7-DEVELOPMENT/decisions/PDR-002-provider-agnostic-core.md)). |
| **Simplicity over features** | Easy to understand and use, even if it means fewer features. Sensible defaults; advanced options behind progressive disclosure. |
| **API-first** | Every capability is accessible via the REST API — the UI is a client, never the only door ([ADR-003](docs/7-DEVELOPMENT/decisions/ADR-003-streamlit-to-nextjs.md)). |
| **Extensibility through standards** | Extension happens through well-defined interfaces (transformations, commands, prompt templates), not forks. |
| **Async-first** | Long-running operations never block the UI or the API ([ADR-004](docs/7-DEVELOPMENT/decisions/ADR-004-background-jobs-surreal-commands.md)). |

### How we evaluate requests

A feature request that conflicts with the IS NOT list or a principle gets closed with a pointer
here — kindly, and with the reasoning. A "no" protects the core value proposition; it's not a
judgment of the idea. If a request keeps coming back and the principle starts to feel wrong,
that's a signal to revisit the principle through a decision record — not to make a quiet exception.

---

## Current Posture

> **Reviewed: 2026-07.** This section is expected to change. Updating it is not a reversal —
> it's a phase change, recorded with a short PDR and an edit here.

**The phase we're in: get the basics working well for everyone before expanding.** Priority goes
to making the core experience (sources, chat, search, notes, podcasts) solid across the full
provider matrix and deployment surface, ahead of new product surfaces.

### Directional constraints

Decisions about the future we haven't made yet — recorded as "which door to keep open":

- **Single-user first, multi-user compatible.** Open Notebook is a single-user tool today, but
  multi-user is under active consideration ([#712](https://github.com/lfnovo/open-notebook/issues/712)).
  New features must not gratuitously preclude multi-user (schema, auth, data scoping)
  ([PDR-001](docs/7-DEVELOPMENT/decisions/PDR-001-single-user-first.md)).
- **Portable by default.** Provider-exclusive capabilities (including paid-only ones) are on the
  table for the future — deliberately, via PDR, never by accident ([PDR-002](docs/7-DEVELOPMENT/decisions/PDR-002-provider-agnostic-core.md)).

### Horizon

The big clusters under consideration — direction, not roadmap; no dates. Each has an umbrella
issue where the thinking happens:

| Cluster | What it is | Where |
|---|---|---|
| **Platform v-next** | SurrealDB v3 migration, possible frontend/backend Docker image split, possible Surreal Commands → Celery move — evaluated together as one coordinated breaking change | [#372](https://github.com/lfnovo/open-notebook/issues/372) · [#378](https://github.com/lfnovo/open-notebook/issues/378) · [#381](https://github.com/lfnovo/open-notebook/issues/381) |
| **Multi-user** | Deep platform redesign: auth, data scoping, what "multi-user" means for a self-hosted tool | [#712](https://github.com/lfnovo/open-notebook/issues/712) |
| **Content modes & artifacts** | The output side: generated artifacts, videos, explainers, presentations, mind maps — as one coherent product surface, not a pile of features | [#203](https://github.com/lfnovo/open-notebook/issues/203) |
| **Agents operating Open Notebook** | Role inversion via MCP: AI agents use Open Notebook on the user's behalf — the platform becomes the research memory of agents, not just a UI | [#878](https://github.com/lfnovo/open-notebook/issues/878) · [#693](https://github.com/lfnovo/open-notebook/issues/693) · [#973](https://github.com/lfnovo/open-notebook/issues/973) |

---

## How this document changes

- **Identity** changes rarely and deliberately: a decision record marks the old rule as
  superseded, then this document is updated.
- **Posture** changes when the phase changes: a short PDR captures the why, the section above is
  edited, and the "Reviewed" stamp is bumped.
- Engineering practices (code standards, anti-patterns, decision framework) live in
  [docs/7-DEVELOPMENT/design-principles.md](docs/7-DEVELOPMENT/design-principles.md).
