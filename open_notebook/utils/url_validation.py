"""
URL validation shared by the credentials API and the AI provisioning layer.

Lives in open_notebook.utils (not api/) so it can be imported both by the API
layer (credential create/update, source-URL ingestion) and by open_notebook's
own AI layer (connection_tester.py, ModelManager) to re-validate a
provider-configured URL immediately before it is actually used - closing most
of the DNS-rebinding TOCTOU window left by validating only once, at save time.
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

# AWS's IMDSv6 metadata endpoint. Unlike the IPv4 metadata address
# (169.254.169.254), this is a Unique Local Address, not link-local, so it is
# not caught by ip.is_link_local and must be checked explicitly.
_AWS_IMDS_V6_ADDRESS = ipaddress.ip_address("fd00:ec2::254")


async def validate_url(url: str, provider: str) -> None:
    """
    Validate URL format for API endpoints.

    This is a self-hosted application, so we allow:
    - Private IPs (10.x, 172.16-31.x, 192.168.x) for self-hosted services
    - Localhost for local services (Ollama, LM Studio, etc.)

    We only block:
    - Invalid schemes (must be http or https)
    - Malformed URLs
    - Link-local addresses (169.254.x.x) - used for cloud metadata endpoints
    - AWS's IPv6 metadata address (fd00:ec2::254)
    - Hostnames that resolve to any of the above

    Args:
        url: The URL to validate
        provider: The provider name (for logging/context)

    Raises:
        ValueError: If the URL is invalid
    """
    if not url or not url.strip():
        return  # Empty URLs handled elsewhere

    try:
        parsed = urlparse(url.strip())

        # Validate scheme - only http/https allowed
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme: '{parsed.scheme}'. Only http and https are allowed."
            )

        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: hostname could not be determined.")

        # Try to parse as IP address to check for dangerous addresses
        try:
            ip = ipaddress.ip_address(hostname)
            _reject_dangerous_ip(ip, hostname)

        except ValueError as ve:
            # Re-raise our own ValueErrors
            if "Link-local" in str(ve) or "Invalid URL" in str(ve) or "metadata" in str(ve):
                raise
            # Not an IP address, it's a hostname - need to resolve and check
            try:
                # Resolve hostname to IP address. This is a blocking call -
                # run it off the event loop so a slow/hanging DNS lookup
                # doesn't stall every other concurrent request (this is
                # called on the hot path of model provisioning, potentially
                # once per chat message/transformation).
                resolved_ips = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
                for family, _, _, _, sockaddr in resolved_ips:
                    ip_addr = sockaddr[0]
                    try:
                        parsed_ip = ipaddress.ip_address(ip_addr)
                        _reject_dangerous_ip(parsed_ip, hostname, resolved=True)
                    except ValueError as inner_ve:
                        if "link-local" in str(inner_ve).lower() or "metadata" in str(inner_ve).lower():
                            raise
                        # Skip non-IP addresses (e.g., IPv6 zones)
                        continue
            except socket.gaierror:
                # Could not resolve hostname - allow it since the URL may be
                # valid in the deployment environment (e.g., Azure endpoints,
                # internal DNS names). We only block link-local addresses.
                pass

    except ValueError:
        raise
    except Exception:
        raise ValueError("Invalid URL format. Check server logs for details.")


def _reject_dangerous_ip(
    ip: "ipaddress.IPv4Address | ipaddress.IPv6Address",
    hostname: str,
    resolved: bool = False,
) -> None:
    """Raise ValueError if `ip` is a link-local or cloud-metadata address."""
    is_ipv4_mapped_link_local = (
        hasattr(ip, "ipv4_mapped") and ip.ipv4_mapped and ip.ipv4_mapped.is_link_local
    )

    # Block link-local addresses (169.254.x.x / fe80::/10) - used for cloud
    # metadata - including IPv4-mapped IPv6 addresses pointing to link-local
    # (e.g. ::ffff:169.254.169.254 bypasses IPv6 is_link_local check).
    if ip.is_link_local or is_ipv4_mapped_link_local:
        if resolved:
            raise ValueError(
                f"Hostname '{hostname}' resolves to a link-local address (169.254.x.x) "
                "which is not allowed for security reasons. These addresses are used "
                "for cloud metadata endpoints."
            )
        raise ValueError(
            "Link-local addresses (169.254.x.x) are not allowed for security reasons. "
            "These addresses are used for cloud metadata endpoints."
        )

    # Block AWS's IMDSv6 metadata address - a Unique Local Address, not
    # link-local, so it needs its own explicit check.
    if ip == _AWS_IMDS_V6_ADDRESS:
        if resolved:
            raise ValueError(
                f"Hostname '{hostname}' resolves to the AWS IMDSv6 metadata address "
                "(fd00:ec2::254), which is not allowed for security reasons."
            )
        raise ValueError(
            "The AWS IMDSv6 metadata address (fd00:ec2::254) is not allowed for "
            "security reasons."
        )
