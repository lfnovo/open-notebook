# ADR-014: Same-host CORS default when no password is set

- **Status**: Accepted
- **Date**: 2026-11
- **Related**: GHSA-j9qj-6wv3-h874, GHSA-86f4-cgrg-6mgx, GHSA-fq8h-7989-x5pc, GHSA-rqgh-qmgp-g768 (tracked in private security advisories, so there is no public issue)

## Context

Authentication is optional: without `OPEN_NOTEBOOK_PASSWORD` the API accepts every request ([PDR-001](PDR-001-single-user-first.md), single user first). The CORS default was `*` regardless of that. Together they meant that any web page the user visited could call an unauthenticated Open Notebook (`http://localhost:5055`) through the user's browser and read the answers: notebooks, sources, which providers are configured. Binding the ports to `127.0.0.1` doesn't help here, because the requests come from the user's own browser.

Several independent security reports flagged the unauthenticated default. Making a password mandatory would break the zero-config local path the project values.

The default UI is itself cross-origin: with `API_URL` unset, the frontend's `/config` route tells the browser to call `<host it was opened from>:5055` from the page on port 8502. A localhost-only default would therefore break every no-password install opened from another machine (LAN, VPS).

## Decision

**While `CORS_ORIGINS` is unset (or blank) and no password is set, the API only accepts browser cross-origin requests from `localhost`, `127.0.0.1` and `[::1]`, and from origins whose host name equals the host name in the request's `Host` header (any port, http or https).** `SameHostCORSMiddleware` in `api/cors.py` extends Starlette's `CORSMiddleware` with that check; credentials are not allowed. With a password set, the default stays `*`. An explicit `CORS_ORIGINS`, including `*`, always wins. The API logs which default is in effect at startup.

The browser sets both `Origin` and `Host`, so a page on another site can't make them match.

## Alternatives considered

- **Require a password**: rejected; it breaks first-run on a laptop, the main use case.
- **Localhost-only default**: rejected; it breaks the default UI opened from another machine (see Context).
- **Bind the default compose ports to `127.0.0.1`**: still open for discussion. It protects against the network, not against web pages in the user's browser, and it breaks LAN and VPS installs that reach port 8502 today.
- **Keep `*` and only document it**: rejected; the cross-site read needs no misconfiguration at all.

## Consequences

- The default UI keeps working from this machine, the LAN or a VPS without any configuration.
- A no-password install whose UI and API are served from different host names (for example behind a reverse proxy) now gets CORS errors. The fix is to set a password or list the UI origin in `CORS_ORIGINS`; the startup log and the CHANGELOG say so.
- Any other page served from the same host name (another app on the same server) is also allowed. That host is already trusted with the network path to the API.
- CORS limits what a page can read and which requests need a preflight. It is not authentication: it does not stop "simple" cross-site requests (for example a form POST) from being sent, and it does not cover DNS-rebinding attacks, where the attacker's host name resolves to the API. A password remains the real protection for anything beyond one person on their own machine.
