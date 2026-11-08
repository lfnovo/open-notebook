"""get_database_url() fallback to the legacy SURREAL_ADDRESS / SURREAL_PORT variables."""

import pytest

from open_notebook.database.repository import get_database_url


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("SURREAL_URL", "SURREAL_ADDRESS", "SURREAL_PORT"):
        monkeypatch.delenv(name, raising=False)


def test_surreal_url_wins(monkeypatch):
    monkeypatch.setenv("SURREAL_URL", "ws://db:8000/rpc")
    monkeypatch.setenv("SURREAL_ADDRESS", "other")
    assert get_database_url() == "ws://db:8000/rpc"


def test_defaults():
    assert get_database_url() == "ws://localhost:8000/rpc"


def test_address_and_port(monkeypatch):
    monkeypatch.setenv("SURREAL_ADDRESS", "db.internal")
    monkeypatch.setenv("SURREAL_PORT", "8018")
    assert get_database_url() == "ws://db.internal:8018/rpc"


def test_bracketed_ipv6_without_port_gets_surreal_port(monkeypatch):
    monkeypatch.setenv("SURREAL_ADDRESS", "[::1]")
    monkeypatch.setenv("SURREAL_PORT", "8018")
    assert get_database_url() == "ws://[::1]:8018/rpc"


def test_bracketed_ipv6_with_port(monkeypatch):
    monkeypatch.setenv("SURREAL_ADDRESS", "[::1]:8000")
    assert get_database_url() == "ws://[::1]:8000/rpc"


def test_address_with_port_ignores_surreal_port(monkeypatch):
    monkeypatch.setenv("SURREAL_ADDRESS", "10.1.2.3:8000")
    monkeypatch.setenv("SURREAL_PORT", "9999")
    assert get_database_url() == "ws://10.1.2.3:8000/rpc"
