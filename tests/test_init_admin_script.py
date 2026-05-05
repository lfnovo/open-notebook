import importlib.util
import sys
from pathlib import Path

import pytest


def load_init_admin_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "init-admin.py"
    spec = importlib.util.spec_from_file_location("init_admin_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class FakeConnection:
    def __init__(self):
        self.queries = []

    async def query(self, query, params=None):
        self.queries.append((query, params or {}))
        if query.startswith("SELECT"):
            return [{"id": "app_user:admin", "username": "admin", "hashed_password": "old"}]
        return [{"id": "app_user:admin"}]


class FakeDbConnection:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_init_admin_force_promotes_existing_admin_user(monkeypatch):
    module = load_init_admin_module()
    conn = FakeConnection()
    monkeypatch.setattr(module, "db_connection", lambda: FakeDbConnection(conn))
    monkeypatch.setattr(module, "parse_record_ids", lambda result: result)
    monkeypatch.setattr(sys, "argv", ["init-admin.py", "--force"])

    await module.main()

    update_query, params = conn.queries[1]
    assert "role = 'admin'" in update_query
    assert "status = 'active'" in update_query
    assert "display_name" in update_query
    assert "password_changed_at" in update_query
    assert str(params["uid"]) == "app_user:admin"
