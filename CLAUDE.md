## Commercialization program

This fork is being turned into a commercial white-label SaaS. Work is executed
in sequenced WORK PACKAGES, one at a time, per the master plan:
  docs/commercialization/open-notebook-master-implementation-plan.md

Rules:
- Read the master plan and the relevant per-directory CLAUDE.md before any change.
- One branch per work package (wp-<n>-<slug>). Never mix packages.
- A package is done only when its acceptance criteria pass AND tests are green.
- Stop and report at the end of each package for human review. Do not roll on.
- Current work package: **WP1 (Licensing & Compliance)** — implementation
  complete, awaiting review. WP0 complete (merged in #1).

WP0 landed: `upstream-base` tag at the fork point (upstream `30c7e2a`, v1.14.0
— not v1.10.0 as the plan states), verified build steps + baselines in
[docs/DEV_SETUP.md](docs/DEV_SETUP.md), characterization tests in
`tests/characterization/`, and a license drift guard
(`scripts/check_licenses.py`) wired into CI. All five acceptance criteria pass.

## Working on this repo

`main` is protected. Direct pushes are rejected **for everyone, admins
included** — all changes go through a PR with these 7 checks green: Backend
Tests / Lint / Typecheck, Frontend Tests / Lint / Build, License Scan.
Branches must be up to date with `main` before merging. No approving review is
required (single maintainer), and force-pushes and branch deletion are
disabled.

Baselines to beat (see [docs/DEV_SETUP.md](docs/DEV_SETUP.md)): backend
coverage 56%, frontend 35.79% statements. Coverage may only go up.

WP1 landed: [LICENSE](LICENSE) carries our copyright above Luis Novo's
(retained, never replace it), generated [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md),
[docs/LICENSE_COMPLIANCE.md](docs/LICENSE_COMPLIANCE.md) (the standing rules),
[docs/PROVIDER_TERMS.md](docs/PROVIDER_TERMS.md) (all 22 providers), and a
pycountry integrity guard.

**Licensing rules — read [docs/LICENSE_COMPLIANCE.md](docs/LICENSE_COMPLIANCE.md)
before adding any dependency.** Never GPL/AGPL; never PyMuPDF (AGPL) or poppler
(GPL); never modify or vendor `pycountry`. `THIRD-PARTY-NOTICES.md` is
generated and **must be regenerated on Linux** — CI fails if it drifts.

Open items carried forward:
- **⚠️ Needs legal sign-off:** SurrealDB BSL position; BSL text inclusion *if*
  the single-container image ships; per-provider terms (esp. the three
  PRC-jurisdiction providers, ElevenLabs commercial audio rights, and model
  weight licences for local inference).
- `asciidoc` (GPLv2+) is purged from the shipped image pending
  lfnovo/content-core#58. When that merges and content-core is bumped, drop the
  Dockerfile purge and the allowlist entry together.
- Rebranding is **WP3**, not done here — the inventory of where brand
  strings/assets live is in LICENSE_COMPLIANCE.md §8.
- Product gap found while testing extraction (not licensing): uploaded `.html`
  files are rejected — only *inline* HTML content is processed — as are
  `.json` and `.png` without Docling enabled.

@AGENTS.md
