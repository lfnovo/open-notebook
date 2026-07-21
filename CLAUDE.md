## Commercialization program

This fork is being turned into a commercial white-label SaaS. Work is executed
in sequenced WORK PACKAGES, one at a time, per the master plan:
  docs/commercialization/open-notebook-master-implementation-plan.md

Rules:
- Read the master plan and the relevant per-directory CLAUDE.md before any change.
- One branch per work package (wp-<n>-<slug>). Never mix packages.
- A package is done only when its acceptance criteria pass AND tests are green.
- Stop and report at the end of each package for human review. Do not roll on.
- Current work package: **WP0 COMPLETE** (merged in #1). Next: WP1 (Licensing).

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

Open items carried into WP1:
- `asciidoc` (GPLv2+) is a transitive runtime dependency of `content-core`.
  It is purged from the shipped image on branch `wp-1-purge-asciidoc`, and
  removal is proposed upstream in lfnovo/content-core#58. Once that merges and
  content-core is bumped, drop both the Dockerfile purge and the allowlist
  entry in `scripts/check_licenses.py` so its return becomes a CI failure.
- Product gap found while testing extraction (not licensing): uploaded `.html`
  files are rejected — only *inline* HTML content is processed — as are
  `.json` and `.png` without Docling enabled.

@AGENTS.md
