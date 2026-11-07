# ADR-014: Localhost-only CORS default when no password is set

- **Status**: Accepted
- **Date**: 2026-11
- **Related**: GHSA-j9qj-6wv3-h874, GHSA-86f4-cgrg-6mgx, GHSA-fq8h-7989-x5pc, GHSA-rqgh-qmgp-g768

## Context

Authentication is optional: without `OPEN_NOTEBOOK_PASSWORD` the API accepts every request ([PDR-001](PDR-001-single-user-first.md), single user first). The CORS default was `*` regardless of that. Together they meant that any web page the user visited could call an unauthenticated Open Notebook (`http://localhost:5055`) through the user's browser and read the answers: notebooks, sources, which providers are configured. Binding the ports to `127.0.0.1` doesn't help here, because the requests come from the user's own browser.

Several independent security reports flagged the unauthenticated default. Making a password mandatory would break the zero-config local path the project values.

## Decision

**While `CORS_ORIGINS` is unset and no password is set, the API only accepts browser cross-origin requests from `localhost`, `127.0.0.1` and `[::1]` (any port, http or https).** It uses Starlette's `allow_origin_regex` (`LOCALHOST_ORIGIN_REGEX` in `api/main.py`) and does not allow credentials. With a password set, the default stays `*`. An explicit `CORS_ORIGINS`, including `*`, always wins. The API logs which default is in effect at startup.

## Alternatives considered

- **Require a password**: rejected; it breaks first-run on a laptop, the main use case.
- **Bind the default compose ports to `127.0.0.1`**: still open for discussion. It protects against the network, not against web pages in the user's browser, and it breaks LAN and VPS installs that reach port 8502 today.
- **Keep `*` and only document it**: rejected; the cross-site read needs no misconfiguration at all.

## Consequences

- The shipped UI is unaffected: by default it reaches the API through its own origin (Next.js rewrites), so no CORS check applies. `make frontend` on `localhost:3000` is a localhost origin.
- An install with no password whose browser calls port 5055 directly from a non-localhost origin (`API_URL` set, UI opened from another machine) now gets CORS errors. The fix is to set a password or list that origin in `CORS_ORIGINS`; the startup log and the CHANGELOG say so.
- CORS limits what a page can read and which requests need a preflight. It does not stop "simple" cross-site requests (for example a form POST) from being sent, and it does not cover DNS-rebinding attacks against localhost. A password remains the real protection for anything beyond one person on their own machine.
