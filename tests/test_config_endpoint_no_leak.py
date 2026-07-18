"""
Regression test for GET /api/config (api/routers/config.py) - an
unauthenticated endpoint (listed in PasswordAuthMiddleware's
excluded_paths).

An earlier audit flagged check_database_health() as leaking raw exception
text to unauthenticated callers. Reading the current code: the exception
string does get put into check_database_health()'s internal return dict
(`error` key), but get_config() only logs that value server-side
(logger.warning) - it never includes it in the JSON response, which
carries just `dbStatus` ("online"/"offline"). This test locks that
contract in so a future edit can't reintroduce the leak by, e.g., adding
`"error": db_health.get("error")` to the response dict.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


SENSITIVE_MESSAGE = "connection refused to internal-db-host.corp.local:8000: password auth failed for user 'root'"


class TestConfigEndpointDoesNotLeakDbErrors:
    def test_db_failure_does_not_include_raw_error_in_response(self, client):
        with patch(
            "api.routers.config.repo_query",
            new=AsyncMock(side_effect=RuntimeError(SENSITIVE_MESSAGE)),
        ):
            response = client.get("/api/config")

        assert response.status_code == 200
        body = response.json()
        assert SENSITIVE_MESSAGE not in response.text
        assert "error" not in body
        assert body["dbStatus"] == "offline"
        assert set(body.keys()) == {"version", "latestVersion", "hasUpdate", "dbStatus"}

    def test_db_timeout_does_not_include_raw_error_in_response(self, client):
        import asyncio

        with patch(
            "api.routers.config.repo_query",
            new=AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            response = client.get("/api/config")

        assert response.status_code == 200
        body = response.json()
        assert "error" not in body
        assert body["dbStatus"] == "offline"

    def test_healthy_db_reports_online(self, client):
        with patch(
            "api.routers.config.repo_query",
            new=AsyncMock(return_value=[{"result": 1}]),
        ):
            response = client.get("/api/config")

        assert response.status_code == 200
        assert response.json()["dbStatus"] == "online"

    def test_config_endpoint_is_unauthenticated(self, client):
        """Sanity check that this endpoint really is reachable without a
        password - the scenario the finding's "unauthenticated" framing
        depends on."""
        response = client.get("/api/config")
        assert response.status_code != 401
