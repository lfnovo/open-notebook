# Gates — what needs a human, what doesn't

The contract that made v1.11.0 safe. When in doubt, ask — a blocked action is
feedback, not an obstacle to route around.

## You may do autonomously (once the release run is underway)

- Run any test, build, probe or analysis; start/stop local dev services
- Create branches, commits, and open PRs
- Spawn subagents (smoke-e2e, investigation, fixes)
- Build/pull Docker images locally; run the release-test harness and RC stack
- Dispatch the *Build and Release* CI workflow with `push_latest=false`
  (version tags only — this is the agreed pre-verification push)

## Requires explicit, in-session authorization from the owner

| Action | Why |
|---|---|
| Merging PRs you authored | two-party review; ask once per session ("merge when clean?") and honor the answer |
| Publishing the GitHub release | public, triggers `v1-latest` — the point of no return |
| Anything that pushes `v1-latest` | users receive it immediately |
| Creating GitHub issues | external artifacts the owner may not want |
| Mass-labeling issues (`released`) | bulk modification of shared state |
| Touching the owner's dev data | only ever work on **copies** (export/import); never mount or mutate originals |

## Never

- Push directly to main
- Publish a prerelease/release to work around a blocked step
- Mark a phase complete with failing checks ("GO with known issues is worse
  than a NO-GO that catches problems before users do")

## Re-test policy after each fix merge

- Cheap suite (pytest + lint + frontend tests/build): **always**
- smoke-e2e / image gate: only if the fix touches what they cover
- Owner's manual verification: only if the fix touches what they verified
- The final image gate (Phase 5.3) always runs on the exact release artifact

## GO/NO-GO

A release is GO when: bucket A fully green · image gate green (fresh +
upgrade) · bucket C signed off by the owner · no open release-regression
findings · Dependabot highs resolved or explicitly accepted.
