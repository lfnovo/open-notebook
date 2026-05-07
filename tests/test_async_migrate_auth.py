from open_notebook.database.async_migrate import AsyncMigrationManager


def test_async_migration_manager_loads_latest_numbered_migrations():
    manager = AsyncMigrationManager()

    assert len(manager.up_migrations) == len(manager.down_migrations) == 31
    assert "workspace_system_policy:global" in manager.up_migrations[-2].sql
    assert "REMOVE TABLE IF EXISTS workspace_system_policy" in manager.down_migrations[-2].sql
    assert "owner_id ON TABLE chat_session" in manager.up_migrations[-1].sql
    assert "REMOVE FIELD IF EXISTS workspace_id ON TABLE chat_session" in manager.down_migrations[-1].sql


def test_async_migration_manager_includes_user_team_share_migration():
    manager = AsyncMigrationManager()

    assert len(manager.up_migrations) >= 21
    assert len(manager.down_migrations) >= 21


def test_async_migration_manager_includes_audit_metadata_flexible_fix():
    manager = AsyncMigrationManager()

    assert len(manager.up_migrations) >= 23
    assert len(manager.down_migrations) >= 23
    assert "metadata ON TABLE audit_log TYPE option<object> FLEXIBLE" in manager.up_migrations[22].sql
