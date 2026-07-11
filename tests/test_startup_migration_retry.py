"""Tests for API startup migration retry behavior."""

from unittest.mock import AsyncMock

import pytest

from api import main as api_main


class FakeMigrationManager:
    def __init__(
        self,
        ping_side_effect=None,
        current_versions=None,
        needs_migration=True,
        migration_side_effect=None,
    ):
        self.ping = AsyncMock(side_effect=ping_side_effect)
        self.get_current_version = AsyncMock(side_effect=current_versions or [14])
        self.needs_migration = AsyncMock(return_value=needs_migration)
        self.run_migration_up = AsyncMock(side_effect=migration_side_effect)


@pytest.fixture
def no_retry_delay(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(api_main, "DATABASE_STARTUP_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(api_main, "DATABASE_STARTUP_RETRY_INITIAL_DELAY_SECONDS", 0)
    monkeypatch.setattr(api_main, "DATABASE_STARTUP_RETRY_MAX_DELAY_SECONDS", 0)
    monkeypatch.setattr(api_main.asyncio, "sleep", sleep)
    return sleep


@pytest.mark.asyncio
async def test_database_reachable_on_first_probe_runs_migrations_once(
    monkeypatch, no_retry_delay
):
    manager = FakeMigrationManager(
        ping_side_effect=[None],
        current_versions=[13, 14],
        needs_migration=True,
    )
    monkeypatch.setattr(api_main, "AsyncMigrationManager", lambda: manager)

    await api_main._run_database_migrations()

    manager.ping.assert_awaited_once()
    manager.run_migration_up.assert_awaited_once()
    assert manager.get_current_version.await_count == 2
    no_retry_delay.assert_not_awaited()


@pytest.mark.asyncio
async def test_database_retry_succeeds_after_initial_probe_failures(
    monkeypatch, no_retry_delay
):
    temporary_error = OSError("Temporary failure in name resolution")
    manager = FakeMigrationManager(
        ping_side_effect=[temporary_error, temporary_error, None],
        current_versions=[13, 14],
        needs_migration=True,
    )
    monkeypatch.setattr(api_main, "AsyncMigrationManager", lambda: manager)

    await api_main._run_database_migrations()

    assert manager.ping.await_count == 3
    assert no_retry_delay.await_count == 2
    manager.run_migration_up.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_raises_after_database_retry_budget_exhausted(
    monkeypatch, no_retry_delay
):
    manager = FakeMigrationManager(
        ping_side_effect=OSError(-3, "Temporary failure in name resolution"),
    )
    monkeypatch.setattr(api_main, "AsyncMigrationManager", lambda: manager)

    with pytest.raises(RuntimeError, match="Failed to run database migrations"):
        # lifespan never touches its app argument, so None keeps the test
        # isolated from the real FastAPI app.
        async with api_main.lifespan(None):  # type: ignore[arg-type]
            pass

    assert manager.ping.await_count == 3
    assert no_retry_delay.await_count == 2
    manager.run_migration_up.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifespan_does_not_retry_real_migration_errors(
    monkeypatch, no_retry_delay
):
    manager = FakeMigrationManager(
        ping_side_effect=[None],
        current_versions=[13],
        needs_migration=True,
        migration_side_effect=ValueError("bad migration"),
    )
    monkeypatch.setattr(api_main, "AsyncMigrationManager", lambda: manager)

    with pytest.raises(RuntimeError, match="Failed to run database migrations"):
        # lifespan never touches its app argument, so None keeps the test
        # isolated from the real FastAPI app.
        async with api_main.lifespan(None):  # type: ignore[arg-type]
            pass

    manager.ping.assert_awaited_once()
    no_retry_delay.assert_not_awaited()
    manager.run_migration_up.assert_awaited_once()
