# ADR-005: Releases pass a risk-based confidence process, gated on the real image

- **Status**: Accepted
- **Date**: 2026-07 (established during the v1.11.0 release)
- **Related**: [RELEASE_PROCESS.md](../../../.github/RELEASE_PROCESS.md), `scripts/release-test/`, [ADR-004](ADR-004-background-workers.md)

## Context

Releases grew from a handful of fixes to 50+ commits spanning security
hardening, features, migrations and dependency changes. Verification was
ad-hoc: a green test suite on `main` plus whatever manual checks the release
owner remembered. v1.11.0 proved the gap empirically — the unit suite was
fully green while `sort_by=title` returned a 500 (a SEARCH-index interaction
only a real SurrealDB exhibits) and clearing credential fields silently
no-oped (two mirror-image bugs, frontend and API, that only an end-to-end
path reveals). Neither class of bug is catchable by mocked tests, and neither
was: both were found by the process this record establishes.

## Decision

**Every stable release passes a risk-based confidence process before cutting,
and the final gate runs against the built Docker image — the artifact users
receive — not the repository.**

The process (mechanics in [RELEASE_PROCESS.md](../../../.github/RELEASE_PROCESS.md)):

1. **Changelog audit first** — the release diff, fully represented in the
   CHANGELOG, is the input for both the test plan and the communication.
2. **Risk matrix over test list** — each change is classified by what it can
   break and for whom, then assigned to a bucket: **A** (automated now),
   **B** (automatable with investment — build the muscle when it compounds),
   **C** (release-owner judgment: real credentials, real TTS, UX, the pushed
   image). Security changes are probed for the inverse risk: does the
   protection break legitimate use?
3. **The image gate** — fresh-install and upgrade-with-data scenarios run
   against real containers (`make release-test`), because packaging bugs
   (supervisord flags, uv sync modes, migration ordering) never appear in the
   suite.
4. **Fix loop with a re-test policy** — findings become focused PRs; what
   re-runs after each merge is defined up front. Pre-existing bugs that are
   not release regressions become backlog issues, not scope creep.
5. **Human gates stay human** — the pushed-image verification and the release
   publication require the release owner explicitly; automation prepares,
   people pull the trigger.
6. **Retro closes the loop** — accepted improvements are applied to the
   process docs and scripts in the same session.

## Alternatives considered

- **Keep ad-hoc verification** — free, but v1.11.0 showed it misses exactly
  the bug classes that hurt users most (integration and packaging).
- **Full CI-based E2E on every PR** — highest coverage, but a real
  SurrealDB + worker + image build pipeline on every PR is slow and expensive;
  the release boundary is where artifact-level confidence pays off.
- **Community soak (RC tags)** — previously abandoned: slow feedback and low
  participation; a deliberate confidence process front-loads what soaking
  found late.

## Consequences

- Cutting a release costs hours, not minutes — deliberately: the cost scales
  with release size, which is the point of the risk matrix.
- Release muscle is versioned in-repo (`scripts/release-test/`, make targets)
  and compounds: bucket-B investments from one release become bucket-A
  automation for the next.
- The upgrade scenario requires published previous images to remain available
  on the registries.
- The process assumes a release owner in the loop for buckets B/C — it is a
  confidence process, not full automation.
