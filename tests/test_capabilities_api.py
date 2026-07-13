"""
Tests for GET /api/capabilities (api/routers/capabilities.py).

The endpoint reports the *actual* availability of the opt-in heavy extraction
runtimes (Docling, Crawl4AI local) so the frontend can gate engine options.
These tests lock the composition rule: crawl4ai_available is true when EITHER a
local package is installed OR a remote server is configured.
"""

import importlib.util

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _patch_probes(monkeypatch, *, docling, crawl4ai_local, crawl4ai_remote):
    monkeypatch.setattr(
        "api.routers.capabilities._docling_available", lambda: docling
    )
    monkeypatch.setattr(
        "api.routers.capabilities._crawl4ai_remote_configured",
        lambda: crawl4ai_remote,
    )
    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name, *args, **kwargs):
        if name == "crawl4ai":
            return object() if crawl4ai_local else None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)


class TestCapabilitiesEndpoint:
    def test_all_unavailable(self, client, monkeypatch):
        _patch_probes(
            monkeypatch, docling=False, crawl4ai_local=False, crawl4ai_remote=False
        )
        response = client.get("/api/capabilities")
        assert response.status_code == 200
        assert response.json() == {
            "docling_available": False,
            "crawl4ai_available": False,
            "crawl4ai_remote_configured": False,
        }

    def test_docling_available_is_independent_of_crawl4ai(self, client, monkeypatch):
        _patch_probes(
            monkeypatch, docling=True, crawl4ai_local=False, crawl4ai_remote=False
        )
        body = client.get("/api/capabilities").json()
        assert body["docling_available"] is True
        assert body["crawl4ai_available"] is False

    def test_local_crawl4ai_makes_it_available(self, client, monkeypatch):
        _patch_probes(
            monkeypatch, docling=False, crawl4ai_local=True, crawl4ai_remote=False
        )
        body = client.get("/api/capabilities").json()
        assert body["crawl4ai_available"] is True
        assert body["crawl4ai_remote_configured"] is False

    def test_remote_crawl4ai_makes_it_available_without_local(
        self, client, monkeypatch
    ):
        _patch_probes(
            monkeypatch, docling=False, crawl4ai_local=False, crawl4ai_remote=True
        )
        body = client.get("/api/capabilities").json()
        assert body["crawl4ai_available"] is True
        assert body["crawl4ai_remote_configured"] is True
