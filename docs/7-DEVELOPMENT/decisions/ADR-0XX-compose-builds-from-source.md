# ADR-0XX: The shipped compose file builds the image instead of pulling it

- **Status**: Accepted
- **Date**: 2026-11
- **Related**: #1412, `docker-compose.yml`, `Dockerfile`

## Context

`docker-compose.yml` is the documented standard install, and it pulled `lfnovo/open_notebook:v1-latest`. That is right for users following releases, but it makes the compose path useless for testing a branch: `docker compose up` runs whatever the published tag points at, never the code under review. A plain `build: .` fixes that and breaks the other half of the audience — a compose file downloaded on its own has no checkout, let alone a `Dockerfile` next to it.

## Decision

The `open_notebook` service builds from the repository instead of pulling: `build: https://github.com/rumplestilzken/open-notebook.git#<sha>`, `pull_policy: build`, tagged `open-notebook:local`.

A remote build context means a downloaded compose file still works on its own, `docker compose up` compiles the code under test, and `pull_policy: build` rebuilds on every `up` rather than reusing a stale image. The context is pinned to a commit rather than the branch tip, so a merge or a push cannot silently swap the running code; bump the SHA when the branch moves.

## Alternatives considered

- **Keep pulling the release image** — the compose path never exercises the code in the repository, which is the gap this PR opened.
- **`build: .`** — needs a checkout plus the `Dockerfile` beside the compose file; the documented "download the file and run it" install loses its context.
- **A separate development compose file** — two files to keep in step, and the shipped one stays untested; it also leaves the contributor's `docker compose up` on the release image unless they know to switch files.

## Consequences

- The shipped file now needs network access and a first `docker compose up` build; that is slower than a pull.
- Until the fork's `main` is folded back, releases following `v1-latest` need the `image:`/`build:` lines pointed back at `lfnovo/open_notebook:v1-latest`; the CHANGELOG entry says so.
- `pull_policy: build` rebuilds on `up`, so local edits are always picked up, at the cost of a rebuild each time.