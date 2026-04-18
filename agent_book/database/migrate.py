import asyncio

from .async_migrate import AsyncMigrationManager


class MigrationManager:
    """
    Synchronous wrapper around AsyncMigrationManager for backward compatibility.
    """

    def __init__(self):
        """Initialize with async migration manager."""
        self._async_manager = AsyncMigrationManager()

    def get_current_version(self) -> int:
        """Get current database version (sync wrapper)."""
        return asyncio.run(self._async_manager.get_current_version())

    @property
    def needs_migration(self) -> bool:
        """Check if migration is needed (sync wrapper)."""
        return asyncio.run(self._async_manager.needs_migration())

    def run_migration_up(self):
        """Run migrations (sync wrapper)."""
        asyncio.run(self._async_manager.run_migration_up())
