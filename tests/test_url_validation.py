"""
Test URL validation for SSRF protection in API key configuration.

Note: The validation is intentionally permissive for self-hosted scenarios.
It only blocks:
- Invalid schemes (must be http or https)
- Malformed URLs
- Link-local addresses (169.254.x.x) - used for cloud metadata endpoints

Localhost and private IPs are ALLOWED because this is a self-hosted application
where users commonly run local services (Ollama, LM Studio, etc.).

validate_url() is async (the hostname-resolution branch runs
socket.getaddrinfo() via asyncio.to_thread so it doesn't block the event
loop - see open_notebook/utils/url_validation.py), so every test here is
async too.
"""

import socket
from unittest.mock import patch

import pytest

from api.credentials_service import validate_url
from open_notebook.utils.url_validation import prepare_pinned_http_target

pytestmark = pytest.mark.asyncio


class TestUrlValidation:
    """Test suite for URL validation to prevent SSRF attacks."""

    async def test_valid_https_url(self):
        """Valid HTTPS URLs should pass."""
        await validate_url("https://api.openai.com", "openai")
        await validate_url("https://example.com/api", "anthropic")
        # Should not raise

    async def test_valid_http_url(self):
        """Valid HTTP URLs should pass."""
        await validate_url("http://example.com", "openai")
        # Should not raise

    async def test_invalid_scheme(self):
        """URLs with invalid schemes should be rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            await validate_url("ftp://example.com", "openai")

        with pytest.raises(ValueError, match="Invalid URL scheme"):
            await validate_url("file:///etc/passwd", "openai")

    async def test_localhost_allowed_for_self_hosted(self):
        """Localhost should be allowed for self-hosted services."""
        # This is a self-hosted app, localhost is valid for local services
        await validate_url("http://localhost:8000", "openai")
        await validate_url("http://127.0.0.1:8000", "azure")
        # Should not raise

    async def test_localhost_allowed_for_ollama(self):
        """Localhost should be allowed for Ollama provider."""
        await validate_url("http://localhost:11434", "ollama")
        await validate_url("http://127.0.0.1:11434", "ollama")
        # Should not raise

    async def test_private_ip_allowed_for_self_hosted(self):
        """Private IP addresses should be allowed for self-hosted scenarios."""
        # This is a self-hosted app, private IPs are valid for internal services
        await validate_url("http://10.0.0.1", "openai")
        await validate_url("http://172.16.0.1:8080", "anthropic")
        await validate_url("http://192.168.1.1", "azure")
        # Should not raise

    async def test_private_ip_allowed_for_ollama(self):
        """Private IP addresses should be allowed for Ollama provider."""
        await validate_url("http://192.168.1.100:11434", "ollama")
        await validate_url("http://10.0.0.50:11434", "ollama")
        # Should not raise

    async def test_loopback_allowed_for_self_hosted(self):
        """Loopback addresses should be allowed for self-hosted scenarios."""
        await validate_url("http://127.0.0.2", "openai")
        # Should not raise

    async def test_link_local_rejection(self):
        """Link-local addresses should be rejected (cloud metadata protection)."""
        with pytest.raises(ValueError, match="Link-local addresses"):
            await validate_url("http://169.254.169.254", "openai")

        # Also reject for ollama - link-local is never valid
        with pytest.raises(ValueError, match="Link-local addresses"):
            await validate_url("http://169.254.169.254", "ollama")

    async def test_ipv6_localhost_allowed(self):
        """IPv6 localhost should be allowed for self-hosted scenarios."""
        await validate_url("http://[::1]:8000", "openai")
        # Should not raise

    async def test_empty_url(self):
        """Empty URLs should not raise (handled elsewhere)."""
        await validate_url("", "openai")
        # None is handled by the function's early return check
        # Should not raise

    async def test_invalid_url_format(self):
        """Malformed URLs should be rejected."""
        with pytest.raises(ValueError):
            await validate_url("not-a-url", "openai")

    async def test_public_hostnames_allowed(self):
        """Public hostnames should be allowed."""
        await validate_url("https://api.openai.com/v1", "openai")
        await validate_url("https://api.anthropic.com", "anthropic")
        await validate_url("https://generativelanguage.googleapis.com", "google")
        await validate_url("https://api.groq.com", "groq")
        # Should not raise

    async def test_azure_specific_urls(self):
        """Azure OpenAI endpoints should be validated."""
        await validate_url(
            "https://my-resource.openai.azure.com", "azure"
        )
        # Localhost is allowed for self-hosted
        await validate_url("http://localhost:8000", "azure")
        # Should not raise

    async def test_openai_compatible_urls(self):
        """OpenAI-compatible provider URLs should be validated."""
        await validate_url("https://api.together.xyz", "openai_compatible")
        # Private IPs are allowed for self-hosted
        await validate_url("http://192.168.1.1:8080", "openai_compatible")
        # Should not raise

    async def test_ipv4_mapped_ipv6_link_local_rejected(self):
        """IPv4-mapped IPv6 addresses pointing to link-local should be rejected."""
        with pytest.raises(ValueError, match="Link-local addresses"):
            await validate_url("http://[::ffff:169.254.169.254]", "openai")

    async def test_ipv4_mapped_ipv6_private_allowed(self):
        """IPv4-mapped IPv6 addresses pointing to private IPs should be allowed."""
        await validate_url("http://[::ffff:192.168.1.1]", "openai")
        # Should not raise - private IPs allowed for self-hosted

    async def test_aws_imds_v6_rejected(self):
        """AWS IMDSv6 metadata address must be rejected."""
        with pytest.raises(ValueError, match="IMDSv6|metadata"):
            await validate_url("http://[fd00:ec2::254]/", "openai")

    async def test_scoped_aws_imds_v6_rejected(self):
        """Scoped IMDSv6 (fd00:ec2::254%eth0) must not bypass the sentinel check."""
        with pytest.raises(ValueError, match="IMDSv6|metadata"):
            await validate_url("http://[fd00:ec2::254%eth0]/", "openai")

        with pytest.raises(ValueError, match="IMDSv6|metadata"):
            await validate_url("http://[fd00:ec2::254%25eth0]/", "openai")


class TestPinnedHttpTarget:
    """DNS pinning closes the validate-then-httpx rebinding window."""

    async def test_ip_literal_unchanged(self):
        target = await prepare_pinned_http_target(
            "http://127.0.0.1:11434/api/tags", "ollama"
        )
        assert target.url == "http://127.0.0.1:11434/api/tags"
        assert target.headers == {}
        assert target.extensions == {}

    async def test_link_local_ip_rejected(self):
        with pytest.raises(ValueError, match="Link-local"):
            await prepare_pinned_http_target(
                "http://169.254.169.254/latest/meta-data", "openai_compatible"
            )

    async def test_scoped_aws_imds_v6_rejected(self):
        """Scoped IMDSv6 literals must be rejected before pinning returns a target."""
        with pytest.raises(ValueError, match="IMDSv6|metadata"):
            await prepare_pinned_http_target(
                "http://[fd00:ec2::254%eth0]/", "openai_compatible"
            )

        with pytest.raises(ValueError, match="IMDSv6|metadata"):
            await prepare_pinned_http_target(
                "http://[fd00:ec2::254%25eth0]/", "openai_compatible"
            )

    async def test_hostname_pinned_to_resolved_ip(self):
        fake_addrs = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.50", 0)),
        ]
        with patch(
            "open_notebook.utils.url_validation.socket.getaddrinfo",
            return_value=fake_addrs,
        ):
            target = await prepare_pinned_http_target(
                "http://ollama.local:11434/api/tags", "ollama"
            )

        assert target.url == "http://192.168.1.50:11434/api/tags"
        assert target.headers == {"Host": "ollama.local:11434"}
        assert target.extensions == {}

    async def test_https_sets_sni_hostname(self):
        fake_addrs = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        ]
        with patch(
            "open_notebook.utils.url_validation.socket.getaddrinfo",
            return_value=fake_addrs,
        ):
            target = await prepare_pinned_http_target(
                "https://api.example.com/v1/models", "openai_compatible"
            )

        assert target.url == "https://93.184.216.34/v1/models"
        assert target.headers == {"Host": "api.example.com"}
        assert target.extensions == {"sni_hostname": "api.example.com"}

    async def test_unicode_hostname_idna_encoded_for_host_and_sni(self):
        """Internationalized hostnames must use ASCII IDNA for Host and SNI."""
        fake_addrs = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        ]
        with patch(
            "open_notebook.utils.url_validation.socket.getaddrinfo",
            return_value=fake_addrs,
        ):
            target = await prepare_pinned_http_target(
                "https://bücher.example/v1/models", "openai_compatible"
            )

        assert target.url == "https://93.184.216.34/v1/models"
        assert target.headers == {"Host": "xn--bcher-kva.example"}
        assert target.extensions == {"sni_hostname": "xn--bcher-kva.example"}

    async def test_hostname_resolving_to_link_local_rejected(self):
        fake_addrs = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 0)),
        ]
        with patch(
            "open_notebook.utils.url_validation.socket.getaddrinfo",
            return_value=fake_addrs,
        ):
            with pytest.raises(ValueError, match="link-local"):
                await prepare_pinned_http_target(
                    "http://evil.example/v1/models", "openai_compatible"
                )
