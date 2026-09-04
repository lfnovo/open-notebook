---
name: release
description: Orchestrate an Open Notebook release — changelog audit, risk-based A/B/C test matrix, Docker image gate (fresh + upgrade), fix loop via PRs, cut, publication with credits, retro. Use when preparing, testing, cutting or publishing a release.
---

# Open Notebook Release Orchestrator

You are conducting a release of Open Notebook, reproducing the process
established in v1.11.0. The **source of truth for the process** is
`.github/RELEASE_PROCESS.md` — read it first. This skill adds the
orchestration order, the exact commands, and the human gates.

**Ground rules for the whole run:**

- The release happens in a **single session**. Track phases with the task
  tools (TaskCreate/TaskUpdate) so the owner sees progress.
- Every repo change goes through a **PR** (branch → PR → CI + cubic → merge).
  Never push to main. Confirm the owner authorizes you to merge your own PRs
  when clean; otherwise hand merges to them.
- Interact in the owner's language; write code, commits and docs in English.
- Read `${CLAUDE_SKILL_DIR}/gates.md` NOW — it defines what you may do
  autonomously and what requires an explicit GO.

## Phase 0 — Scope and changelog audit

1. `git fetch --tags` · find the last release tag and `gh release list`.
2. List everything merged since: `git log <last-tag>..origin/main --oneline`.
3. Audit the CHANGELOG `[Unreleased]` section against that list. Convention:
   entries reference the **issue** number when one exists, the PR number
   otherwise. Close every gap via PR.
4. Check open Dependabot alerts (`gh api repos/{owner}/{repo}/dependabot/alerts?state=open`)
   — a security-themed release with open highs is incoherent. Triage them
   into the fix loop or document acceptance.

## Phase 1 — Risk-based test matrix

Read `${CLAUDE_SKILL_DIR}/test-matrix.md` and instantiate it against the
actual release diff. Classify each change: what can it break, for whom,
which bucket (A/B/C) verifies it. **Refine the matrix with the owner before
executing** — they decide bucket-B investments and own bucket C.

## Phase 2 — Execute bucket A

Run in parallel where possible:

- `uv run pytest tests/` · `ruff check .` · `uv run python -m mypy .` (all three
  are required CI gates since the July 2026 cleanup; mypy must exit 0)
- Frontend: `npm run lint`, `npm run test`, `npm run build` (production build;
  a stale `node_modules` produces false build failures — `npm ci` first if so)
- The **smoke-e2e agent** against the local dev stack (start it: database →
  api → worker → frontend; check ports are free first — another project may
  hold 3000/8000: identify the owner via `lsof` + process cwd, never kill
  blind; the frontend runs fine on `PORT=3001 npm run dev` — pass the URL to
  the smoke agent. Also note the dev `.env` may point at a standalone
  SurrealDB, not the repo-compose one)
- **Dev-DB leak check**: snapshot per-table record counts (at least
  credentials) before and after the backend suite — a diff means a test is
  writing to the live database (caught 48 leaked credentials in v1.12.0)
- The **targeted probes** from the matrix (legitimate-use regression checks
  for security changes)

## Phase 3 — Image gate + bucket C kickoff

- `make docker-build-local`, then `make release-test TAG=<ver> OLD_TAG=<prev>`
  (pull the genuine previous tag first — see gotchas in RELEASE_PROCESS.md).
- Hand the owner their bucket-C checklist (from the matrix) so they test in
  parallel — do not leave them as the bottleneck at the end.

## Phase 4 — Fix loop

For each finding: reproduce → root-cause → focused PR with regression tests →
CI + cubic → merge (per gates.md). Apply the re-test policy from
RELEASE_PROCESS.md after each merge. Pre-existing bugs that are not release
regressions become backlog issues (ask the owner before creating issues).
Verify UI fixes in the real browser (Playwright) before opening the PR.

## Phase 5 — Cut

1. Cut PR off updated main: bump `pyproject.toml`, date the changelog section.
2. After merge: `make tag`.
3. Rebuild the image from final main and **re-run the image gate** against it.
4. Push version images via CI:
   `gh workflow run build-and-release.yml --ref main -f push_latest=false`
   and watch the run. (Local `make docker-push` needs `docker login`.)
5. Verify the pushed manifests (see `${CLAUDE_SKILL_DIR}/runbook.md`).

## Phase 6 — Pushed-image verification (human gate)

Offer the owner a browsable RC stack on this machine:
`make release-stack TAG=<ver> [DUMP=<dump>]` — with a copy of their dev data
for realism (export command in the runbook). Support them through it; findings
go back to Phase 4. **Do not proceed without their GO.**

## Phase 7 — Publish (human gate)

1. Draft release notes per `${CLAUDE_SKILL_DIR}/comms-templates.md` — the
   **Thanks section is mandatory**; collect every contributor with the
   commands in the template. Show the owner for review.
2. With their explicit GO: `gh release create v<ver> --title ... --notes-file ... --latest`.
   Publication triggers CI to push `v1-latest` — watch it, then verify the
   latest manifests (runbook).
3. Mark shipped issues with the `released` label (ask before mass-labeling).
4. Deliver the Discord post text (the owner posts it).

## Phase 8 — Cleanup

`make release-stack-down`, remove temp dumps/data dirs, stop watchers, ensure
`git status` is clean on main and no test containers remain.

## Phase 9 — Retro (always runs)

Ask the owner: *"what should improve in this process?"* — and apply the
accepted improvements **now**: edit `.github/RELEASE_PROCESS.md`,
`scripts/release-test/*`, and this skill's files while context is fresh.
New gotchas discovered during the run go into RELEASE_PROCESS.md's Known
Gotchas via the same PR flow.
