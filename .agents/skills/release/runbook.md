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
for ref in lfnovo/open_notebook:<ver> lfnovo/open_notebook:<ver>-single ghcr.io/lfnovo/open-notebook:<ver>; do
  docker manifest inspect "$ref" | python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(set(m['platform']['architecture'] for m in d.get('manifests',[]) if m['platform']['architecture']!='unknown')))"
done
# expect ['amd64', 'arm64'] for each; repeat with v1-latest after publication
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
