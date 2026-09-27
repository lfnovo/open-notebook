"""Core integration port for the optional, build-installed retrieval module."""
from open_notebook.modules.registry import Registry, ModuleError


class SearchAdapter:
    @staticmethod
    def enabled():
        registry = Registry()
        return 'hybrid-search' in registry.installed and registry.active('hybrid-search')

    @staticmethod
    def engine():
        if not SearchAdapter.enabled():
            raise ModuleError('Hybrid search is disabled. Enable it in Settings → Modules settings.')
        from open_notebook.modules.hybrid_search.service import engine
        if engine.periodic is None or engine.periodic.done():
            import asyncio
            engine.periodic = asyncio.create_task(engine.run_periodic())
        return engine

    @staticmethod
    async def start():
        if SearchAdapter.enabled():
            SearchAdapter.engine()

    @staticmethod
    async def close():
        # Module may have been disabled since startup: still close owned tasks.
        import sys
        loaded = sys.modules.get('open_notebook.modules.hybrid_search.service')
        if loaded:
            await loaded.engine.close()
