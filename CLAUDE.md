## Commercialization program

This fork is being turned into a commercial white-label SaaS. Work is executed
in sequenced WORK PACKAGES, one at a time, per the master plan:
  docs/commercialization/open-notebook-master-implementation-plan.md

Rules:
- Read the master plan and the relevant per-directory CLAUDE.md before any change.
- One branch per work package (wp-<n>-<slug>). Never mix packages.
- A package is done only when its acceptance criteria pass AND tests are green.
- Stop and report at the end of each package for human review. Do not roll on.
- Current work package: **WP2 (Identity & Microsoft Entra ID auth)** — in
  progress (kickoff). WP0, WP1, and WP-DEC are complete on `main`.

WP0 landed: `upstream-base` tag at the fork point (upstream `30c7e2a`, v1.14.0
— not v1.10.0 as the plan states), verified build steps + baselines in
[docs/DEV_SETUP.md](docs/DEV_SETUP.md), characterization tests in
`tests/characterization/`, and a license drift guard
(`scripts/check_licenses.py`) wired into CI. All five acceptance criteria pass.
Merged in PRs #1–#2.

WP1 landed: [LICENSE](LICENSE) carries our copyright above Luis Novo's
(retained, never replace it), generated [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md),
[docs/LICENSE_COMPLIANCE.md](docs/LICENSE_COMPLIANCE.md) (the standing rules),
[docs/PROVIDER_TERMS.md](docs/PROVIDER_TERMS.md) (all 22 providers),
[docs/LEGAL_DECISIONS.md](docs/LEGAL_DECISIONS.md), BSL text in the
single-container image, and a pycountry integrity guard. Merged in PRs #3–#5.

WP-DEC landed: **Model A (single-tenant per client)** — documented in
[docs/TENANCY.md](docs/TENANCY.md). WP2, WP3, WP5, and WP7 are built against this.

Program task schedule (WBS):  
[docs/commercialization/Open-Notebook-Commercialization-WBS-Task-Schedule.xlsx](docs/commercialization/Open-Notebook-Commercialization-WBS-Task-Schedule.xlsx)

## Working on this repo

`main` is protected. Direct pushes are rejected **for everyone, admins
included** — all changes go through a PR with these 7 checks green: Backend
Tests / Lint / Typecheck, Frontend Tests / Lint / Build, License Scan.
Branches must be up to date with `main` before merging. No approving review is
required (single maintainer), and force-pushes and branch deletion are
disabled.

Baselines to beat (see [docs/DEV_SETUP.md](docs/DEV_SETUP.md)): backend
coverage 56%, frontend 35.79% statements. Coverage may only go up.

**Licensing rules — read [docs/LICENSE_COMPLIANCE.md](docs/LICENSE_COMPLIANCE.md)
before adding any dependency.** Never GPL/AGPL; never PyMuPDF (AGPL) or poppler
(GPL); never modify or vendor `pycountry`. `THIRD-PARTY-NOTICES.md` is
generated and **must be regenerated on Linux** — CI fails if it drifts.

Open items carried forward (not WP2 blockers unless noted):
- Customer ToS wording for model-weight and customer-configured endpoint
  responsibility ([LEGAL_DECISIONS.md](docs/LEGAL_DECISIONS.md) items 5–6).
- PRC-jurisdiction providers (DeepSeek, DashScope, MiniMax) should become
  **opt-in per deployment**, not default-on (item 3) — track in WP2/WP3 UI.
- Re-verify [PROVIDER_TERMS.md](docs/PROVIDER_TERMS.md) links before commercial
  launch.
- `asciidoc` (GPLv2+) is purged from the shipped image pending
  lfnovo/content-core#58. When that merges and content-core is bumped, drop the
  Dockerfile purge and the allowlist entry together.
- Rebranding is **WP3** — brand string/asset inventory is in
  LICENSE_COMPLIANCE.md §8.
- Product gaps found while testing (not licensing): uploaded `.html` files are
  rejected — only *inline* HTML content is processed — as are `.json` and
  `.png` without Docling enabled; Azure credential form still needs an
  `api_version` field in the UI.

@AGENTS.md
