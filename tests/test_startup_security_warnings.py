"""Startup warnings for unsafe default security configuration."""

from unittest.mock import AsyncMock

import pytest

from api import main as api_main
from open_notebook.utils.encryption import DEFAULT_ENCRYPTION_KEY


@pytest.mark.asyncio
async def test_lifespan_warns_for_public_key_and_missing_password(monkeypatch):
    values = {
        "OPEN_NOTEBOOK_ENCRYPTION_KEY": DEFAULT_ENCRYPTION_KEY,
        "OPEN_NOTEBOOK_PASSWORD": None,
    }
    monkeypatch.setattr(api_main, "get_secret_from_env", values.get)
    monkeypatch.setattr(api_main, "_run_database_migrations", AsyncMock())
    warnings: list[str] = []
    monkeypatch.setattr(api_main.logger, "warning", warnings.append)

    async with api_main.lifespan(None):  # type: ignore[arg-type]
        pass

    assert any("public example value" in message for message in warnings)
    assert any("OPEN_NOTEBOOK_PASSWORD not set" in message for message in warnings)


@pytest.mark.asyncio
async def test_lifespan_does_not_warn_for_custom_file_loaded_secrets(
    monkeypatch, tmp_path
):
    key_file = tmp_path / "encryption-key"
    password_file = tmp_path / "password"
    key_file.write_text("private-test-key")
    password_file.write_text("private-test-password")
    monkeypatch.delenv("OPEN_NOTEBOOK_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("OPEN_NOTEBOOK_PASSWORD", raising=False)
    monkeypatch.setenv("OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE", str(key_file))
    monkeypatch.setenv("OPEN_NOTEBOOK_PASSWORD_FILE", str(password_file))
    monkeypatch.setattr(api_main, "_run_database_migrations", AsyncMock())
    warnings: list[str] = []
    monkeypatch.setattr(api_main.logger, "warning", warnings.append)

    async with api_main.lifespan(None):  # type: ignore[arg-type]
        pass

    assert not any("OPEN_NOTEBOOK_ENCRYPTION_KEY" in message for message in warnings)
    assert not any("OPEN_NOTEBOOK_PASSWORD" in message for message in warnings)
