# Runbook — exact commands for the cut-and-publish phases

Gotchas live in `.github/RELEASE_PROCESS.md` → Known Gotchas. This file is
the command reference.

## Version images via CI (Phase 5)

```bash
gh workflow run build-and-release.yml --ref main -f push_latest=false
gh run list --workflow=build-and-release.yml --limit 1     # grab the id
gh run watch <run-id> --exit-status                        # background it
```

## Verify pushed manifests

```bash
for ref in lfnovo/open_notebook:<ver> lfnovo/open_notebook:<ver>-single ghcr.io/lfnovo/open-notebook:<ver> ghcr.io/lfnovo/open-notebook:<ver>-single; do
  docker manifest inspect "$ref" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(set(m['platform']['architecture'] for m in d.get('manifests',[]) if m['platform']['architecture']!='unknown')))"
done
# expect ['amd64', 'arm64'] for all four (`make docker-push` publishes both
# registries × {plain, -single}); repeat with v1-latest and v1-latest-single
# on both registries after publication
```

## RC stack with a copy of the owner's dev data (Phase 6)

```bash
# 1. Find which SurrealDB instance dev actually uses — read SURREAL_URL in .env
#    (multiple instances may run locally; the repo-compose one on :8000 may NOT
#    be it), and note SURREAL_DATABASE.
# 2. Consistent export from the RUNNING instance (originals untouched):
docker exec <that-container> /surreal export --conn http://localhost:8000 \
  --user root --pass root --ns open_notebook --db <that-db> /dev/stdout > /tmp/dev-dump.surql
# 3. Boot (rc-stack.sh docker-pulls the pushed tag by default, so a local
#    build can't shadow the registry artifact):
make release-stack TAG=<ver> DUMP=/tmp/dev-dump.surql
#    To exercise the opt-in heavy runtimes (Docling + Crawl4AI) on the pushed
#    image with this data, append the flag (first boot installs them, ~minutes):
#    bash scripts/release-test/rc-stack.sh up <ver> /tmp/dev-dump.surql --with-runtimes
# 4. Sanity: credentials decrypt (uses the dev encryption key from .env):
curl -s http://localhost:15055/api/credentials | python3 -c "import json,sys; c=json.load(sys.stdin); print(len(c), 'creds,', sum(1 for x in c if x.get('decryption_error')), 'decrypt errors')"
# 5. Opt-in gating is only meaningful on this fresh image (a dev venv may have
#    the runtimes installed out-of-band): GET /api/capabilities should report
#    both false until --with-runtimes installs them.
```

Remind the owner: in-container credentials pointing at host services need
`http://host.docker.internal:<port>` (Ollama, LM Studio).

## Publish (Phase 7 — after explicit GO)

```bash
gh release create v<ver> --title "v<ver> — <theme>" --notes-file <notes.md> --latest
# publication (non-prerelease) triggers the workflow that pushes v1-latest
gh run list --workflow=build-and-release.yml --limit 1 && gh run watch <id> --exit-status
```

## Re-cut after a post-tag fix (Phase 4 ↔ 5 loop)

When a blocker is found *after* the tag exists but *before* publication (no
GitHub release, no `v1-latest` yet), the fix goes through the normal PR flow,
then the release is re-cut. `pyproject.toml` stays at the same version — the tag
moves to the new commit. Exact sequence:

```bash
# 1. Fix merged to main; sync and confirm the version is unchanged
git checkout main && git pull && grep '^version' pyproject.toml   # still <ver>

# 2. Cheap suite (re-test policy) before re-tagging
uv run pytest tests/ -q && ruff check .        # + frontend if it was touched

# 3. Move the tag: delete local + remote, recreate on the new HEAD
git tag -d v<ver>
git push origin :refs/tags/v<ver>
make tag                                       # recreates v<ver> on HEAD
git rev-parse v<ver> && git rev-parse HEAD      # must match

# 4. Rebuild the image and RE-RUN THE IMAGE GATE on the re-cut artifact
docker rmi lfnovo/open_notebook:<ver> lfnovo/open_notebook:local 2>/dev/null
make docker-build-local
make release-test TAG=<ver> OLD_TAG=<prev>     # fresh + upgrade + probes

# 5. Re-push the version images from the fixed commit (overwrites the stale ones)
gh workflow run build-and-release.yml --ref main -f push_latest=false
#    then watch the run and re-verify the <ver> manifests (section above)

# 6. Re-boot the RC stack on the fresh pushed image for the owner's re-GO
make release-stack TAG=<ver> DUMP=<dump>
```

Only after the owner re-GOes does publication proceed. The published-release CI
run promotes whatever the version tag/images currently are to `v1-latest`, so a
skipped rebuild here means users get the un-fixed artifact.

## Label shipped issues (after owner OK)

```bash
# only actual closed ISSUES (changelog refs mix issues and PR numbers):
for n in <numbers>; do
  STATE=$(gh api "repos/lfnovo/open-notebook/issues/$n" --jq 'if .pull_request then "pr" else .state end')
  [ "$STATE" = "closed" ] && gh issue edit "$n" --add-label released
done
```

## Cleanup (Phase 8)

```bash
make release-stack-down
rm -f /tmp/dev-dump.surql; rm -rf /tmp/onrel-*
docker ps --format '{{.Names}}' | grep onrel   # must be empty
git status --short                              # must be clean on main
```
