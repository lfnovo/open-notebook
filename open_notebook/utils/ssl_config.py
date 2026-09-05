"""SSL settings shared by Esperanto providers and raw httpx clients.

Connection tests and model discovery use httpx directly. Those paths must
honor the same ESPERANTO_SSL_* environment variables documented for Esperanto,
otherwise corporate / self-signed HTTPS endpoints pass chat but fail
"Test Connection" / Discover Models with a misleading ConnectError.
"""

from __future__ import annotations

import os
from typing import Union

# Keep names aligned with esperanto.utils.ssl
SSL_VERIFY_ENV_VAR = "ESPERANTO_SSL_VERIFY"
SSL_CA_BUNDLE_ENV_VAR = "ESPERANTO_SSL_CA_BUNDLE"


def httpx_verify_setting() -> Union[bool, str]:
    """Return a value suitable for ``httpx.AsyncClient(verify=...)``.

    Priority (highest first), matching Esperanto's SSLMixin:

    1. ``ESPERANTO_SSL_CA_BUNDLE`` — path to a CA bundle file
    2. ``ESPERANTO_SSL_VERIFY=false|0|no`` — disable verification
    3. Default — ``True`` (system trust store)

    Raises:
        ValueError: If ``ESPERANTO_SSL_CA_BUNDLE`` is set but the file is
            missing. Esperanto rejects invalid bundles instead of falling
            through to ``ESPERANTO_SSL_VERIFY``; we do the same so Test
            Connection cannot silently disable TLS when a CA path is wrong.
    """
    ca_bundle = os.getenv(SSL_CA_BUNDLE_ENV_VAR)
    if ca_bundle:
        if not os.path.isfile(ca_bundle):
            raise ValueError(f"CA bundle file not found: {ca_bundle}")
        return ca_bundle

    verify_env = os.getenv(SSL_VERIFY_ENV_VAR, "").lower()
    if verify_env in ("false", "0", "no"):
        return False

    return True
