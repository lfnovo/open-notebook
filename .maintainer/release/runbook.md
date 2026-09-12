# Release runbook

The sequence and the policy of a release of this repository, in one place. The plugin's
`release` skill supplies the steps and the gates; `profile.toml` holds the executable
references (`[commands.validator]`, `[commands.frontend]`, `[artifacts.docker].gate`,
`[release].distribution_trigger`); this file holds what those fields cannot express: order,
environment, manual steps, exact command sequences and the reasons behind them. The human
process and its known gotchas live in [`.github/RELEASE_PROCESS.md`](../../.github/RELEASE_PROCESS.md)
(designed in [ADR-005](../../docs/7-DEVELOPMENT/decisions/ADR-005-release-confidence-process.md));
this file does not repeat them.

## Policy

- A release happens in a **single session**, phase by phase, with the owner seeing progress.
- Every repository change goes through a **PR** (branch → PR → CI + cubic → merge). Never push
  to `main`. Merging own PRs: ask once per session and honor the answer (`merge_own_prs`).
- Autonomous: tests, builds, probes, local services, branches, commits, PRs, local image
  builds, the image gate, the RC stack, and dispatching *Build and Release* with
  `push_latest=false` (version tags only — the agreed pre-verification push).
- Explicit in-session GO required: publishing the GitHub release (the point of no return —
  it promotes `v1-latest`), anything else that moves `v1-latest`, creating issues, mass
  labeling (`released`), touching the owner's dev data (copies only, never originals).
- Never: publish a prerelease or release to route around a blocked step; mark a phase
  complete with failing checks ("GO with known issues is worse than a NO-GO").
- **Re-test policy after each fix merge**: the cheap suite (validator + frontend) always;
  smoke-e2e and the image gate only if the fix touches what they cover; the owner's manual
  checks only if the fix touches what they verified; the final image gate always runs on the
  exact release artifact.
- **GO** when: validator and frontend green · image gate green (fresh + upgrade) · owner's
  checks signed off · release notes approved · no open release-regression findings ·
  Dependabot highs resolved or explicitly accepted.

## Validate

- Canonical validator and mandatory checks: `[commands.validator]`, `[commands.frontend]`,
  `[release.gates].mandatory`. Run `uv sync --extra dev` first if mypy is missing locally;
  `npm ci` in `frontend/` if dependencies changed (a stale `node_modules` fakes build failures).
- Bucket A also runs the **smoke-e2e** skill against the local dev stack (database → api →
  worker → frontend; see `[smoke]`) and the **dev-DB leak check** (per-table counts before
  and after the backend suite).
- Artifact gate: `[artifacts.docker].gate`, built from the candidate commit.
  `docker-build-local` tags with the current `pyproject.toml` version, so `docker pull` the
  genuine previous tag before the upgrade scenario.
- Environment or credentials the checks need (names only, never values):
  - `.env` with `OPEN_NOTEBOOK_ENCRYPTION_KEY` and a `SURREAL_URL` (check which local
    SurrealDB it points at), at least one provider credential with chat + embedding defaults
  - Docker with buildx; `docker login` on both registries only for the local push fallback
  - `gh` authenticated with `workflow` scope (dispatching *Build and Release*)

## Owner's manual checks

Delivered as a concrete checklist tailored to what the release touched and to the
credentials the owner has (`GET /api/credentials` tells you). Standing items:

- Provider connection tests with **real credentials** (prioritize providers whose code
  changed); one discover-models; one chat per main provider.
- One podcast with real TTS on a dense notebook.
- Visual/UX tour (~10 min) of every UI change, plus dark-mode sampling.
- The pushed image on the RC stack (see *Verify from the registry*).

Verify error-path items against the provisioning code before listing them: transformation
and tools defaults deliberately fall back to the chat default (`open_notebook/ai/models.py`).

## Cut

- The cut is the **last** step, on its own branch, committed immediately: bump
  `pyproject.toml`, run `[release].lock_command`, date `[Unreleased]` as `[<ver>] - <date>`,
  open the cut PR. Never carry an uncommitted bump across branches.
- After merge: `make tag` (creates and pushes `v<ver>` from `pyproject.toml`).

## Publish, only after the GO

- Trigger: `[release].distribution_trigger` — pushes `<ver>` and `<ver>-single` to Docker
  Hub and GHCR (both arches). Watch it:

```bash
gh run list --workflow=build-and-release.yml --limit 1     # grab the id
gh run watch <run-id> --exit-status
```

- Then verify from the registry (next section) and, on the owner's re-GO, promote:

```bash
gh release create v<ver> --title "v<ver> — <theme>" --notes-file <notes.md> --latest
# publication (non-prerelease) re-runs the workflow, which pushes v1-latest and v1-latest-single
gh run list --workflow=build-and-release.yml --limit 1 && gh run watch <id> --exit-status
```

- Release notes follow `.github/RELEASE_PROCESS.md` → Communication (verdict, sections,
  behavior changes for self-hosters, **Thanks** by handle — never skipped). Announcement text
  for Discord is delivered to the owner after `v1-latest` is live.

## Verify from the registry

```bash
for ref in lfnovo/open_notebook:<ver> lfnovo/open_notebook:<ver>-single ghcr.io/lfnovo/open-notebook:<ver> ghcr.io/lfnovo/open-notebook:<ver>-single; do
  docker manifest inspect "$ref" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(set(m['platform']['architecture'] for m in d.get('manifests',[]) if m['platform']['architecture']!='unknown')))"
done
# expect ['amd64', 'arm64'] for all four; repeat with v1-latest and v1-latest-single after publication
```

RC stack on the pushed image, optionally with a copy of the owner's dev data (copies only):

```bash
# 1. Find which SurrealDB instance dev uses: SURREAL_URL and SURREAL_DATABASE in .env
# 2. Consistent export from the RUNNING instance (originals untouched)
docker exec <that-container> /surreal export --conn http://localhost:8000 \
  --user root --pass root --ns open_notebook --db <that-db> /dev/stdout > /tmp/dev-dump.surql
# 3. Boot (rc-stack.sh docker-pulls the tag, so a local build cannot shadow the registry artifact)
make release-stack TAG=<ver> DUMP=/tmp/dev-dump.surql
#    opt-in heavy runtimes on the pushed image (first boot installs them, minutes):
#    bash scripts/release-test/rc-stack.sh up <ver> /tmp/dev-dump.surql --with-runtimes
# 4. Credentials decrypt with the dev key from .env
curl -s http://localhost:15055/api/credentials | python3 -c "import json,sys; c=json.load(sys.stdin); print(len(c), 'creds,', sum(1 for x in c if x.get('decryption_error')), 'decrypt errors')"
# 5. GET /api/capabilities reports docling/crawl4ai false until --with-runtimes installs them
```

## Re-cut after a post-tag fix

A blocker found after the tag exists but before publication: the fix goes through the normal
PR flow, the version stays, the tag moves, **and the images are rebuilt and re-gated** — a
stale tag or registry image is what publication would promote.

```bash
git checkout main && git pull && grep '^version' pyproject.toml   # still <ver>
uv run pytest tests/ -q && ruff check .                            # + frontend if touched
git tag -d v<ver> && git push origin :refs/tags/v<ver> && make tag
git rev-parse v<ver> && git rev-parse HEAD                          # must match
docker rmi lfnovo/open_notebook:<ver> lfnovo/open_notebook:local 2>/dev/null
make docker-build-local && make release-test TAG=<ver> OLD_TAG=<prev>
gh workflow run build-and-release.yml --ref main -f push_latest=false   # overwrites the stale images
# re-verify the manifests, re-boot the RC stack, wait for the owner's re-GO
```

## After publication

Label shipped issues `released` (after the owner's OK; only actual closed issues — changelog
references mix issue and PR numbers):

```bash
for n in <numbers>; do
  STATE=$(gh api "repos/lfnovo/open-notebook/issues/$n" --jq 'if .pull_request then "pr" else .state end')
  [ "$STATE" = "closed" ] && gh issue edit "$n" --add-label released
done
```

## Cleanup

```bash
make release-stack-down
rm -f /tmp/dev-dump.surql; rm -rf /tmp/onrel-*
docker ps --format '{{.Names}}' | grep onrel   # must be empty
git status --short                              # must be clean on main
```

## Retro

Close every release by asking what should improve. Apply the accepted improvements
immediately: this file, `.github/RELEASE_PROCESS.md`, `scripts/release-test/`, `gotchas.md`
and the decision log, while the context is fresh.
