"""
Test URL validation for SSRF protection in API key configuration.

Note: The validation is intentionally permissive for self-hosted scenarios.
It only blocks:
- Invalid schemes (must be http or https)
- Malformed URLs
- Link-local addresses (169.254.x.x) - used for cloud metadata endpoints

Localhost and private IPs are ALLOWED because this is a self-hosted application
where users commonly run local services (Ollama, LM Studio, etc.).
"""

import pytest

from api.credentials_service import validate_url


class TestUrlValidation:
    """Test suite for URL validation to prevent SSRF attacks."""

    def test_valid_https_url(self):
        """Valid HTTPS URLs should pass."""
        validate_url("https://api.openai.com", "openai")
        validate_url("https://example.com/api", "anthropic")
        # Should not raise

    def test_valid_http_url(self):
        """Valid HTTP URLs should pass."""
        validate_url("http://example.com", "openai")
        # Should not raise

    def test_invalid_scheme(self):
        """URLs with invalid schemes should be rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("ftp://example.com", "openai")

        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("file:///etc/passwd", "openai")

    def test_localhost_allowed_for_self_hosted(self):
        """Localhost should be allowed for self-hosted services."""
        # This is a self-hosted app, localhost is valid for local services
        validate_url("http://localhost:8000", "openai")
        validate_url("http://127.0.0.1:8000", "azure")
        # Should not raise

    def test_localhost_allowed_for_ollama(self):
        """Localhost should be allowed for Ollama provider."""
        validate_url("http://localhost:11434", "ollama")
        validate_url("http://127.0.0.1:11434", "ollama")
        # Should not raise

    def test_private_ip_allowed_for_self_hosted(self):
        """Private IP addresses should be allowed for self-hosted scenarios."""
        # This is a self-hosted app, private IPs are valid for internal services
        validate_url("http://10.0.0.1", "openai")
        validate_url("http://172.16.0.1:8080", "anthropic")
        validate_url("http://192.168.1.1", "azure")
        # Should not raise

    def test_private_ip_allowed_for_ollama(self):
        """Private IP addresses should be allowed for Ollama provider."""
        validate_url("http://192.168.1.100:11434", "ollama")
        validate_url("http://10.0.0.50:11434", "ollama")
        # Should not raise

    def test_loopback_allowed_for_self_hosted(self):
        """Loopback addresses should be allowed for self-hosted scenarios."""
        validate_url("http://127.0.0.2", "openai")
        # Should not raise

    def test_link_local_rejection(self):
        """Link-local addresses should be rejected (cloud metadata protection)."""
        with pytest.raises(ValueError, match="Link-local addresses"):
            validate_url("http://169.254.169.254", "openai")

        # Also reject for ollama - link-local is never valid
        with pytest.raises(ValueError, match="Link-local addresses"):
            validate_url("http://169.254.169.254", "ollama")

    def test_ipv6_localhost_allowed(self):
        """IPv6 localhost should be allowed for self-hosted scenarios."""
        validate_url("http://[::1]:8000", "openai")
        # Should not raise

    def test_empty_url(self):
        """Empty URLs should not raise (handled elsewhere)."""
        validate_url("", "openai")
        # None is handled by the function's early return check
        # Should not raise

    def test_invalid_url_format(self):
        """Malformed URLs should be rejected."""
        with pytest.raises(ValueError):
            validate_url("not-a-url", "openai")

    def test_public_hostnames_allowed(self):
        """Public hostnames should be allowed."""
        validate_url("https://api.openai.com/v1", "openai")
        validate_url("https://api.anthropic.com", "anthropic")
        validate_url("https://generativelanguage.googleapis.com", "google")
        validate_url("https://api.groq.com", "groq")
        # Should not raise

    def test_azure_specific_urls(self):
        """Azure OpenAI endpoints should be validated."""
        validate_url(
            "https://my-resource.openai.azure.com", "azure"
        )
        # Localhost is allowed for self-hosted
        validate_url("http://localhost:8000", "azure")
        # Should not raise

    def test_openai_compatible_urls(self):
        """OpenAI-compatible provider URLs should be validated."""
        validate_url("https://api.together.xyz", "openai_compatible")
        # Private IPs are allowed for self-hosted
        validate_url("http://192.168.1.1:8080", "openai_compatible")
        # Should not raise

    def test_ipv4_mapped_ipv6_link_local_rejected(self):
        """IPv4-mapped IPv6 addresses pointing to link-local should be rejected."""
        with pytest.raises(ValueError, match="Link-local addresses"):
            validate_url("http://[::ffff:169.254.169.254]", "openai")

    def test_ipv4_mapped_ipv6_private_allowed(self):
        """IPv4-mapped IPv6 addresses pointing to private IPs should be allowed."""
        validate_url("http://[::ffff:192.168.1.1]", "openai")
        # Should not raise - private IPs allowed for self-hosted
