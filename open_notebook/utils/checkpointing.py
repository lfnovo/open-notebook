"""Async checkpointer bridge for the SqliteSaver-backed chat graphs.

The chat graphs keep their checkpoints in a module-level synchronous SQLite
connection (`LANGGRAPH_CHECKPOINT_FILE`). Making the graph nodes async lets the
API stream a node's tokens with `graph.astream(..., stream_mode="messages")`
and *cancel* the provider request when the client disconnects; LangGraph's async
run path then wants an async checkpointer, but `SqliteSaver`'s async methods
raise `NotImplementedError`.

`HybridSqliteSaver` closes that gap: it keeps the sync connection (and every
sync `get_state`/`update_state` caller) working, and delegates each async method
to the sync one on a worker thread so `astream`/`aget_state` work without
migrating the file-based checkpoint store to a different backend.

The per-node SQLite work (a checkpoint write per super-step) is small next to
the model call, so the thread hop costs nothing measurable per turn.

This module exists so both chat graphs can share one implementation: when the
source-chat graph is converted to an async node it should import this class
rather than copy it.
"""

import asyncio
from typing import Any, AsyncIterator, Optional, Sequence, Tuple

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.sqlite import SqliteSaver


class HybridSqliteSaver(SqliteSaver):
    """`SqliteSaver` with async delegates for LangGraph's async run path."""

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        return await asyncio.to_thread(self.get_tuple, config)

    async def aget(self, config: RunnableConfig) -> Optional[Checkpoint]:
        return await asyncio.to_thread(self.get, config)  # type: ignore[attr-defined]

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        items = await asyncio.to_thread(
            lambda: list(self.list(config, filter=filter, before=before, limit=limit))
        )
        for item in items:
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return await asyncio.to_thread(
            self.put, config, checkpoint, metadata, new_versions
        )

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        return await asyncio.to_thread(
            self.put_writes, config, writes, task_id, task_path
        )

    async def adelete_thread(self, thread_id: str) -> None:
        return await asyncio.to_thread(self.delete_thread, thread_id)


# Re-exported for type checkers that want the base class at hand.
__all__ = ["HybridSqliteSaver", "BaseCheckpointSaver"]
