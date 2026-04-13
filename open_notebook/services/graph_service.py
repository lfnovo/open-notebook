"""
GraphService — per-workspace LightRAG instance management.

Provides graph-based knowledge extraction and hybrid query (vector + graph + keyword)
for each workspace. LightRAG instances are lazily initialized and cached with LRU
eviction. Degrades gracefully when LightRAG is not installed.
"""

import asyncio
import os
import re
import shutil
from collections import OrderedDict
from typing import Any, Dict, Optional

from loguru import logger

from open_notebook.services.lightrag_adapter import build_embedding_func, build_llm_func


def _try_import_lightrag():
    """
    Attempt to import LightRAG at runtime.

    Returns the module on success, None on import failure.
    This allows the system to degrade gracefully when
    LightRAG and its dependencies are absent.
    """
    try:
        import lightrag

        return lightrag
    except ImportError:
        logger.warning(
            "LightRAG (lightrag-hku) is not installed. "
            "Knowledge graph features will be unavailable. "
            "Install with: pip install lightrag-hku"
        )
        return None


class GraphService:
    """
    Manages per-workspace LightRAG instances with LRU eviction.

    All methods are classmethods — this service is not instantiated.
    Thread safety is ensured via asyncio.Lock for lazy initialization.
    """

    DATA_ROOT: str = os.path.join("data")
    MAX_CACHED: int = 20

    _instances: OrderedDict = OrderedDict()
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    def _graph_dir(cls, workspace_id: str) -> str:
        # Prevent path traversal
        safe_id = workspace_id.replace(":", "_")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", safe_id):
            raise ValueError(f"Invalid workspace_id format: {workspace_id}")
        graph_path = os.path.join(cls.DATA_ROOT, "graphs", safe_id)
        # Verify the resolved path is under DATA_ROOT
        resolved = os.path.realpath(graph_path)
        expected_root = os.path.realpath(os.path.join(cls.DATA_ROOT, "graphs"))
        if not resolved.startswith(expected_root):
            raise ValueError(
                f"Path traversal detected for workspace_id: {workspace_id}"
            )
        return graph_path

    @classmethod
    async def get_instance(cls, workspace_id: str) -> Optional[Any]:
        """
        Get or create a LightRAG instance for the given workspace.

        Creates the working directory if needed. Returns None when
        LightRAG is not installed.
        """
        async with cls._get_lock():
            if workspace_id in cls._instances:
                cls._instances.move_to_end(workspace_id)
                return cls._instances[workspace_id]

            lightrag_module = _try_import_lightrag()
            if lightrag_module is None:
                return None

            working_dir = cls._graph_dir(workspace_id)
            os.makedirs(working_dir, exist_ok=True)

            llm_func = await build_llm_func()
            embedding_func = await build_embedding_func()

            instance = lightrag_module.LightRAG(
                working_dir=working_dir,
                llm_model_func=llm_func,
                embedding_func=embedding_func,
            )

            cls._instances[workspace_id] = instance

            if len(cls._instances) > cls.MAX_CACHED:
                evicted_key, _ = cls._instances.popitem(last=False)
                logger.info(
                    f"LRU evicted LightRAG instance for workspace {evicted_key}"
                )

            return instance

    @classmethod
    async def insert(cls, workspace_id: str, text: str) -> None:
        """
        Insert text into the workspace's knowledge graph.

        No-op when LightRAG is not available.
        """
        instance = await cls.get_instance(workspace_id)
        if instance is None:
            logger.debug(
                f"Skipping graph insert for workspace {workspace_id}: "
                "LightRAG not available"
            )
            return

        await instance.ainsert(text)

    @classmethod
    async def query(cls, workspace_id: str, query_text: str) -> str:
        """
        Query the workspace's knowledge graph using hybrid mode.

        Returns an empty string when LightRAG is not available.
        """
        instance = await cls.get_instance(workspace_id)
        if instance is None:
            logger.debug(
                f"Skipping graph query for workspace {workspace_id}: "
                "LightRAG not available"
            )
            return ""

        lightrag_module = _try_import_lightrag()
        if lightrag_module is None:
            return ""

        query_param = lightrag_module.QueryParam(mode="hybrid")
        return await instance.aquery(query_text, param=query_param)

    @classmethod
    async def delete_workspace(cls, workspace_id: str) -> None:
        """
        Remove all graph data for a workspace.

        Evicts the cached instance and removes the working directory.
        """
        async with cls._get_lock():
            cls._instances.pop(workspace_id, None)

        graph_dir = cls._graph_dir(workspace_id)
        if os.path.exists(graph_dir):
            try:
                shutil.rmtree(graph_dir)
                logger.info(
                    f"Removed graph data directory for workspace {workspace_id}"
                )
            except Exception as error:
                logger.warning(f"Failed to remove graph directory {graph_dir}: {error}")
