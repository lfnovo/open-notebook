"""Tests for ESPERANTO_SSL_* → httpx verify mapping."""

from pathlib import Path

import pytest

from open_notebook.utils.ssl_config import httpx_verify_setting


@pytest.fixture(autouse=True)
def _clear_ssl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ESPERANTO_SSL_VERIFY", raising=False)
    monkeypatch.delenv("ESPERANTO_SSL_CA_BUNDLE", raising=False)


def test_default_verify_enabled() -> None:
    assert httpx_verify_setting() is True


@pytest.mark.parametrize("value", ["false", "0", "no", "FALSE", "No"])
def test_verify_disabled_via_env(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ESPERANTO_SSL_VERIFY", value)
    assert httpx_verify_setting() is False


def test_ca_bundle_takes_priority_over_verify_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ca = tmp_path / "ca.pem"
    ca.write_text("dummy-ca\n", encoding="utf-8")
    monkeypatch.setenv("ESPERANTO_SSL_CA_BUNDLE", str(ca))
    monkeypatch.setenv("ESPERANTO_SSL_VERIFY", "false")
    assert httpx_verify_setting() == str(ca)


def test_missing_ca_bundle_raises_instead_of_falling_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Misconfigured CA must not silently honor ESPERANTO_SSL_VERIFY=false."""
    monkeypatch.setenv("ESPERANTO_SSL_CA_BUNDLE", "/no/such/ca.pem")
    monkeypatch.setenv("ESPERANTO_SSL_VERIFY", "false")
    with pytest.raises(ValueError, match="CA bundle file not found"):
        httpx_verify_setting()
