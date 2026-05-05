from open_notebook.database.async_migrate import AsyncMigrationManager


def test_async_migration_manager_includes_user_team_share_migration():
    manager = AsyncMigrationManager()

    assert len(manager.up_migrations) >= 21
    assert len(manager.down_migrations) >= 21
