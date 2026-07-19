"""Proxy environment helpers.

Defensive handling for HTTP proxy setups (issue #1160).

``websockets`` 15.0 started auto-detecting ``HTTP_PROXY`` / ``HTTPS_PROXY``
from the environment and tunnels *every* connection through the proxy,
including plain ``ws://`` ones. The SurrealDB SDK connects to the database
over a websocket, so when a proxy is configured the *internal* DB connection
(e.g. ``ws://host.docker.internal:8018/rpc`` or ``ws://surrealdb:8000/rpc``)
gets routed through the external proxy, which rejects the internal host with
HTTP 403 and kills the API / worker on startup.

To make this robust regardless of user configuration, we inject the internal
DB hosts into the ``no_proxy`` / ``NO_PROXY`` env vars at startup (merged with
any user-provided value, never clobbering it). ``urllib.request.proxy_bypass``
- which ``websockets`` calls to decide whether to tunnel - reads these vars,
so the internal websocket is left un-proxied.
"""

import os

# Hosts the DB is reachable at internally. These must never be routed through
# an external proxy. Covers Docker (host.docker.internal, surrealdb service
# name) and local (localhost / 127.0.0.1) topologies.
INTERNAL_NO_PROXY_HOSTS = (
    "host.docker.internal",
    "surrealdb",
    "localhost",
    "127.0.0.1",
)

# urllib.request.proxy_bypass_environment reads the lowercase var first, then
# falls back to the uppercase one. We keep both in sync so the internal hosts
# are honored no matter which variant a user set.
_NO_PROXY_ENV_VARS = ("no_proxy", "NO_PROXY")


def _split_hosts(value: str) -> list[str]:
    return [h.strip() for h in value.split(",") if h.strip()]


def ensure_internal_no_proxy() -> None:
    """Ensure internal DB hosts bypass any configured proxy.

    Merges :data:`INTERNAL_NO_PROXY_HOSTS` into both ``no_proxy`` and
    ``NO_PROXY`` (preserving existing entries and their order) and writes the
    combined value back to both env vars. Idempotent - safe to call more than
    once and from multiple entrypoints (API + worker).
    """
    # Collect existing entries from whichever variants the user set, de-duped
    # while preserving order.
    existing: list[str] = []
    seen: set[str] = set()
    for var in _NO_PROXY_ENV_VARS:
        for host in _split_hosts(os.environ.get(var, "")):
            key = host.lower()
            if key not in seen:
                seen.add(key)
                existing.append(host)

    # Append internal hosts that aren't already present.
    merged = list(existing)
    for host in INTERNAL_NO_PROXY_HOSTS:
        if host.lower() not in seen:
            seen.add(host.lower())
            merged.append(host)

    combined = ",".join(merged)
    for var in _NO_PROXY_ENV_VARS:
        os.environ[var] = combined
