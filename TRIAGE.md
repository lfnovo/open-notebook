# Triage Rules — Open Notebook

Project-specific triage rules. The `/triage` loop provides the **mechanism**; this file is the
**jurisprudence** for this repo. Keep it the single source of truth for how we label issues.

## State funnel (outcome of triage)

Every open issue lands in exactly **one** state. **Untriaged = no state label** — that's what
`/triage` scans for.

| Label | Meaning |
|---|---|
| *(none)* | Not triaged yet. |
| `needs-vision` | Unsure if/how this fits — strategic call for the maintainers. |
| `needs-design` | Wanted, but the *how* isn't resolved — needs design/spec before it's ready. |
| `needs-info` | Waiting on the reporter to confirm or provide more information. |
| `ready` | Fully specified — the dev loop can pick it up. |
| **Close** | Use GitHub's native close reasons (duplicate / not planned). Link the canonical issue when duplicate/superseded. |

## Type

What kind of work it is. Apply one when it's clear.

- `bug` · `enhancement` · `documentation`

> `installation` is an **intake** label applied by the issue-creation workflow (not by triage).
> During triage, installation reports are routed to `area: deploy`.

## Area — apply ALWAYS (one per issue)

Which part of the system. This is the axis we use to route work and surface contributor-friendly
tasks, so every triaged issue should get one area when it clearly belongs to one.

| Label | What goes here |
|---|---|
| `area: chat` | Conversation/chat, RAG retrieval, agentic responses, citations |
| `area: search` | Full-text and semantic search |
| `area: sources` | Source ingestion & processing (URLs, files, content extraction, chunking) |
| `area: notebooks` | Notebook features: notes, insights, transformations |
| `area: providers` | AI provider integrations + model configuration (OpenAI, Ollama, …) |
| `area: embeddings` | Embedding models, vectorization, semantic indexing |
| `area: podcast` | Podcast / audio generation |
| `area: database` | SurrealDB, persistence, schema, migrations |
| `area: ui` | Frontend (Next.js), UX, visual issues |
| `area: deploy` | Docker, deployment, k8s, reverse proxy, infra/setup |
| `area: offline` | Airgapped/offline operation (tokenizer caching, no network) |
| `area: i18n` | Internationalization / localization |

## Bundling / epics

- `umbrella` — a tracking issue grouping related work.
- `tracked-in-umbrella` — covered by an umbrella; follow the umbrella for progress.
- `bundled` — part of a thematic bundle.
- `upstream` — root cause lives in one of our libraries (below), not in this repo.

### Consolidation: one issue vs. umbrella

When several open issues circle the same topic, pick the model by **how decided the work is** —
not just by shared theme. The trap is filing many half-formed issues for a topic that isn't yet
decidable work; that inflates the backlog and reads as "90 things to do" when it's ~30 themes.

- **Pre-vision / pre-design topic** → collapse into **one** issue (`needs-vision` or `needs-design`),
  capture each request's signal (👍 counts, interested contributors) in its body, and **close the
  rest as duplicates** pointing to it. A topic isn't N issues — it's one thinking space.
- **Already decomposed into real parallel tasks** → use `umbrella` + `tracked-in-umbrella`. Children
  stay open because each is independently pickable (e.g. the multi-user umbrella #712).

Rule of thumb: if the issues can't be worked until *we* make a call, they're one issue. If the call
is made and the work splits into things a contributor could pick up today, they're an umbrella with
children. **Never close an issue that has an active assignee/contributor or open PR** — link it as a
phase instead.

## Ecosystem (our own libraries)

Mark issues whose real home is an upstream lib:

- `esperanto` — model abstraction layer (LLM / embedding / TTS / STT).
- `content-core` — content extraction.
- `podcast-creator` — podcast generation library.

## Community

- `good first issue` — small, well-scoped, newcomer-friendly.
- `help wanted` — we'd welcome a contributor to take this.

## Rules

- Assign **one state**, **one type**, and **one area** where each applies. Multiple
  bundling/ecosystem labels are fine.
- `/triage` output must always carry a state (or be closed). Don't leave issues stateless.
- **Don't invent labels** — the set is curated. If something doesn't fit, raise it instead of adding a label.
- When closing as duplicate/superseded, link the canonical issue.
