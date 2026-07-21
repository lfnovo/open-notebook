## Commercialization program

This fork is being turned into a commercial white-label SaaS. Work is executed
in sequenced WORK PACKAGES, one at a time, per the master plan:
  docs/commercialization/open-notebook-master-implementation-plan.md

Rules:
- Read the master plan and the relevant per-directory CLAUDE.md before any change.
- One branch per work package (wp-<n>-<slug>). Never mix packages.
- A package is done only when its acceptance criteria pass AND tests are green.
- Stop and report at the end of each package for human review. Do not roll on.
- Current work package: WP0 (Foundations) — implementation complete, awaiting review.

WP0 landed: `upstream-base` tag at the fork point (upstream `30c7e2a`, v1.14.0
— not v1.10.0 as the plan states), verified build steps + baselines in
[docs/DEV_SETUP.md](docs/DEV_SETUP.md), characterization tests in
`tests/characterization/`, and a license drift guard
(`scripts/check_licenses.py`) wired into CI.

Open items carried out of WP0:
- Branch protection on `main` is NOT yet enabled (needs the branch pushed first).
- `asciidoc` (GPLv2+) is a transitive runtime dependency of `content-core` and
  is allowlisted pending WP1 legal review. It is the one strong-copyleft
  dependency inherited from upstream.

@AGENTS.md
