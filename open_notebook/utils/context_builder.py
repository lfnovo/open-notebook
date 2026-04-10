# """
# Generic ContextBuilder for the Open Notebook project.

# This module provides a flexible ContextBuilder class that can handle any parameters
# and build context from sources, notebooks, insights, and notes.
# """

# from __future__ import annotations

# from dataclasses import dataclass
# from typing import Any, Dict, List, Literal, Optional

# from loguru import logger

# from open_notebook.domain.notebook import Note, Notebook, Source
# from open_notebook.exceptions import DatabaseOperationError, NotFoundError

# from .token_utils import token_count


# @dataclass
# class ContextItem:
#     """Represents a single item in the context."""

#     id: str
#     type: Literal["source", "note", "insight"]
#     content: Dict[str, Any]
#     priority: int = 0
#     token_count: Optional[int] = None

#     def __post_init__(self):
#         """Calculate token count for the content if not provided."""
#         if self.token_count is None:
#             content_str = str(self.content)
#             self.token_count = token_count(content_str)


# @dataclass
# class ContextConfig:
#     """Configuration for context building."""

#     sources: Optional[Dict[str, str]] = None  # {source_id: inclusion_level}
#     notes: Optional[Dict[str, str]] = None  # {note_id: inclusion_level}
#     include_insights: bool = True
#     include_notes: bool = True
#     max_tokens: Optional[int] = None
#     priority_weights: Optional[Dict[str, int]] = None  # {type: weight}

#     def __post_init__(self):
#         """Initialize default values."""
#         if self.sources is None:
#             self.sources = {}
#         if self.notes is None:
#             self.notes = {}
#         if self.priority_weights is None:
#             self.priority_weights = {"source": 100, "note": 50, "insight": 75}


# class ContextBuilder:
#     """
#     Generic ContextBuilder that can handle any parameters and build context
#     from sources, notebooks, insights, and notes.
#     """

#     def __init__(self, **kwargs):
#         """
#         Initialize ContextBuilder with flexible parameters.

#         Supported parameters:
#         - source_id: str - Include specific source
#         - notebook_id: str - Include notebook content
#         - include_insights: bool - Include source insights
#         - include_notes: bool - Include notes
#         - context_config: ContextConfig - Custom context configuration
#         - max_tokens: int - Maximum token limit
#         - priority_order: List[str] - Custom priority order
#         """
#         # Store all parameters for flexibility
#         self.params = kwargs

#         # Extract commonly used parameters
#         self.source_id: Optional[str] = kwargs.get("source_id")
#         self.notebook_id: Optional[str] = kwargs.get("notebook_id")
#         self.include_insights: bool = kwargs.get("include_insights", True)
#         self.include_notes: bool = kwargs.get("include_notes", True)
#         self.max_tokens: Optional[int] = kwargs.get("max_tokens")

#         # Context configuration
#         context_config_arg: Optional[ContextConfig] = kwargs.get("context_config")
#         self.context_config: ContextConfig
#         if context_config_arg is None:
#             self.context_config = ContextConfig(
#                 include_insights=self.include_insights,
#                 include_notes=self.include_notes,
#                 max_tokens=self.max_tokens,
#             )
#         else:
#             self.context_config = context_config_arg

#         # Items storage
#         self.items: List[ContextItem] = []

#         logger.debug(f"ContextBuilder initialized with params: {list(kwargs.keys())}")

#     async def build(self) -> Dict[str, Any]:
#         """
#         Build context based on provided parameters.

#         Returns:
#             Dict containing the built context with metadata
#         """
#         try:
#             logger.info("Starting context building")

#             # Clear existing items
#             self.items = []

#             # Build context based on parameters
#             if self.source_id:
#                 await self._add_source_context(self.source_id)

#             if self.notebook_id:
#                 await self._add_notebook_context(self.notebook_id)

#             # Process any additional custom parameters
#             await self._process_custom_params()

#             # Apply post-processing
#             self.remove_duplicates()
#             self.prioritize()

#             if self.max_tokens:
#                 self.truncate_to_fit(self.max_tokens)

#             # Format and return response
#             return self._format_response()

#         except Exception as e:
#             logger.error(f"Error building context: {str(e)}")
#             raise DatabaseOperationError(f"Failed to build context: {str(e)}")

#     async def _add_source_context(
#         self, source_id: str, inclusion_level: str = "insights"
#     ) -> None:
#         """
#         Add source and its insights to context.

#         Args:
#             source_id: ID of the source
#             inclusion_level: "insights", "full content", or "not in"
#         """
#         if inclusion_level == "not in":
#             return

#         try:
#             # Ensure source ID has table prefix
#             full_source_id = (
#                 source_id if source_id.startswith("source:") else f"source:{source_id}"
#             )

#             source = await Source.get(full_source_id)
#             if not source:
#                 logger.warning(f"Source {source_id} not found")
#                 return

#             # Determine context size based on inclusion level
#             context_size: Literal["short", "long"] = (
#                 "long" if "full content" in inclusion_level else "short"
#             )
#             source_context = await source.get_context(context_size=context_size)

#             # Add source item
#             priority = (self.context_config.priority_weights or {}).get("source", 100)
#             item = ContextItem(
#                 id=source.id or "",
#                 type="source",
#                 content=source_context,
#                 priority=priority,
#             )
#             self.add_item(item)

#             # Add insights if requested and available
#             if self.include_insights and "insights" in inclusion_level:
#                 insights = await source.get_insights()
#                 for insight in insights:
#                     insight_priority = (self.context_config.priority_weights or {}).get(
#                         "insight", 75
#                     )
#                     insight_item = ContextItem(
#                         id=insight.id or "",
#                         type="insight",
#                         content={
#                             "id": insight.id,
#                             "source_id": source.id,
#                             "insight_type": insight.insight_type,
#                             "content": insight.content,
#                         },
#                         priority=insight_priority,
#                     )
#                     self.add_item(insight_item)

#             logger.debug(f"Added source context for {source_id}")

#         except NotFoundError:
#             logger.warning(f"Source {source_id} not found")
#         except Exception as e:
#             logger.error(f"Error adding source context for {source_id}: {str(e)}")
#             raise

#     async def _add_notebook_context(self, notebook_id: str) -> None:
#         """
#         Add notebook content based on context configuration.

#         Args:
#             notebook_id: ID of the notebook
#         """
#         try:
#             notebook = await Notebook.get(notebook_id)
#             if not notebook:
#                 raise NotFoundError(f"Notebook {notebook_id} not found")

#             # Process sources from context config or get all
#             config_sources = self.context_config.sources
#             if config_sources:
#                 for source_id, status in config_sources.items():
#                     await self._add_source_context(source_id, status)
#             else:
#                 # Default: get all sources with insights
#                 sources = await notebook.get_sources()
#                 for source in sources:
#                     if source.id:
#                         await self._add_source_context(source.id, "insights")

#             # Process notes from context config or get all
#             if self.include_notes:
#                 config_notes = self.context_config.notes
#                 if config_notes:
#                     for note_id, status in config_notes.items():
#                         if "not in" not in status:
#                             await self._add_note_context(note_id, status)
#                 else:
#                     # Default: get all notes with short content
#                     notes = await notebook.get_notes()
#                     for note in notes:
#                         if note.id:
#                             await self._add_note_context(note.id, "full content")

#             logger.debug(f"Added notebook context for {notebook_id}")

#         except Exception as e:
#             logger.error(f"Error adding notebook context for {notebook_id}: {str(e)}")
#             raise

#     async def _add_note_context(
#         self, note_id: str, inclusion_level: str = "full content"
#     ) -> None:
#         """
#         Add note to context.

#         Args:
#             note_id: ID of the note
#             inclusion_level: "full content" or "not in"
#         """
#         if inclusion_level == "not in":
#             return

#         try:
#             # Ensure note ID has table prefix
#             full_note_id = note_id if note_id.startswith("note:") else f"note:{note_id}"

#             note = await Note.get(full_note_id)
#             if not note:
#                 logger.warning(f"Note {note_id} not found")
#                 return

#             # Get note context
#             context_size: Literal["short", "long"] = (
#                 "long" if "full content" in inclusion_level else "short"
#             )
#             note_context = note.get_context(context_size=context_size)

#             # Add note item
#             priority = (self.context_config.priority_weights or {}).get("note", 50)
#             item = ContextItem(
#                 id=note.id or "", type="note", content=note_context, priority=priority
#             )
#             self.add_item(item)

#             logger.debug(f"Added note context for {note_id}")

#         except NotFoundError:
#             logger.warning(f"Note {note_id} not found")
#         except Exception as e:
#             logger.error(f"Error adding note context for {note_id}: {str(e)}")

#     async def _process_custom_params(self) -> None:
#         """Process any additional custom parameters."""
#         # Hook for future extensions - can be overridden in subclasses
#         # or used to process additional kwargs
#         for key, value in self.params.items():
#             if key.startswith("custom_"):
#                 logger.debug(f"Processing custom parameter: {key}={value}")
#                 # Custom processing logic can be added here

#     def add_item(self, item: ContextItem) -> None:
#         """
#         Add a ContextItem to the builder.

#         Args:
#             item: ContextItem to add
#         """
#         self.items.append(item)
#         logger.debug(f"Added item {item.id} with priority {item.priority}")

#     def prioritize(self) -> None:
#         """Sort items by priority (higher priority first)."""
#         self.items.sort(key=lambda x: x.priority, reverse=True)
#         logger.debug(f"Prioritized {len(self.items)} items")

#     def truncate_to_fit(self, max_tokens: int) -> None:
#         """
#         Remove items if total token count exceeds limit.

#         Args:
#             max_tokens: Maximum allowed tokens
#         """
#         if not max_tokens:
#             return

#         total_tokens = sum(item.token_count or 0 for item in self.items)

#         if total_tokens <= max_tokens:
#             logger.debug(f"Token count {total_tokens} within limit {max_tokens}")
#             return

#         logger.info(f"Truncating from {total_tokens} to {max_tokens} tokens")

#         # Remove items from the end (lowest priority) until under limit
#         current_tokens = total_tokens
#         removed_count = 0

#         while current_tokens > max_tokens and self.items:
#             removed_item = self.items.pop()
#             current_tokens -= removed_item.token_count or 0
#             removed_count += 1

#         logger.info(
#             f"Removed {removed_count} items, final token count: {current_tokens}"
#         )

#     def remove_duplicates(self) -> None:
#         """Remove duplicate items based on ID."""
#         seen_ids = set()
#         deduplicated_items = []

#         for item in self.items:
#             if item.id not in seen_ids:
#                 deduplicated_items.append(item)
#                 seen_ids.add(item.id)

#         removed_count = len(self.items) - len(deduplicated_items)
#         self.items = deduplicated_items

#         if removed_count > 0:
#             logger.debug(f"Removed {removed_count} duplicate items")

#     def _format_response(self) -> Dict[str, Any]:
#         """
#         Format the final response.

#         Returns:
#             Formatted context response
#         """
#         # Group items by type
#         sources = []
#         notes = []
#         insights = []

#         for item in self.items:
#             if item.type == "source":
#                 sources.append(item.content)
#             elif item.type == "note":
#                 notes.append(item.content)
#             elif item.type == "insight":
#                 insights.append(item.content)

#         # Calculate total tokens
#         total_tokens = sum(item.token_count or 0 for item in self.items)

#         response = {
#             "sources": sources,
#             "notes": notes,
#             "insights": insights,
#             "total_tokens": total_tokens,
#             "total_items": len(self.items),
#             "metadata": {
#                 "source_count": len(sources),
#                 "note_count": len(notes),
#                 "insight_count": len(insights),
#                 "config": {
#                     "include_insights": self.include_insights,
#                     "include_notes": self.include_notes,
#                     "max_tokens": self.max_tokens,
#                 },
#             },
#         }

#         # Add notebook_id if provided
#         if self.notebook_id:
#             response["notebook_id"] = self.notebook_id

#         logger.info(
#             f"Built context with {len(self.items)} items, {total_tokens} tokens"
#         )

#         return response


# # Convenience functions for common use cases


# async def build_notebook_context(
#     notebook_id: str,
#     context_config: Optional[ContextConfig] = None,
#     max_tokens: Optional[int] = None,
# ) -> Dict[str, Any]:
#     """
#     Build context for a notebook.

#     Args:
#         notebook_id: ID of the notebook
#         context_config: Optional context configuration
#         max_tokens: Optional token limit

#     Returns:
#         Built context
#     """
#     builder = ContextBuilder(
#         notebook_id=notebook_id, context_config=context_config, max_tokens=max_tokens
#     )
#     return await builder.build()


# async def build_source_context(
#     source_id: str, include_insights: bool = True, max_tokens: Optional[int] = None
# ) -> Dict[str, Any]:
#     """
#     Build context for a single source.

#     Args:
#         source_id: ID of the source
#         include_insights: Whether to include insights
#         max_tokens: Optional token limit

#     Returns:
#         Built context
#     """
#     builder = ContextBuilder(
#         source_id=source_id, include_insights=include_insights, max_tokens=max_tokens
#     )
#     return await builder.build()


# async def build_mixed_context(
#     source_ids: Optional[List[str]] = None,
#     note_ids: Optional[List[str]] = None,
#     notebook_id: Optional[str] = None,
#     max_tokens: Optional[int] = None,
# ) -> Dict[str, Any]:
#     """
#     Build context from mixed sources.

#     Args:
#         source_ids: List of source IDs
#         note_ids: List of note IDs
#         notebook_id: Optional notebook ID
#         max_tokens: Optional token limit

#     Returns:
#         Built context
#     """
#     context_config = ContextConfig(max_tokens=max_tokens)

#     # Configure sources
#     if source_ids:
#         context_config.sources = {sid: "insights" for sid in source_ids}

#     # Configure notes
#     if note_ids:
#         context_config.notes = {nid: "full content" for nid in note_ids}

#     builder = ContextBuilder(
#         notebook_id=notebook_id, context_config=context_config, max_tokens=max_tokens
#     )
#     return await builder.build()





"""
Generic ContextBuilder for the Open Notebook project (UPDATED).

Fixes:
- ✅ Strict source-only mode (no external leakage)
- ✅ Optional insights (disabled by default recommended)
- ✅ Better logging (start → end + tokens)
- ✅ Controlled token usage
- ✅ Prevent irrelevant notebook fetch
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from loguru import logger

from open_notebook.domain.notebook import Note, Notebook, Source
from open_notebook.exceptions import DatabaseOperationError, NotFoundError

from .token_utils import token_count


# =========================
# DATA CLASSES
# =========================

@dataclass
class ContextItem:
    id: str
    type: Literal["source", "note", "insight"]
    content: Dict[str, Any]
    priority: int = 0
    token_count: Optional[int] = None

    def __post_init__(self):
        if self.token_count is None:
            self.token_count = token_count(str(self.content))


@dataclass
class ContextConfig:
    sources: Optional[Dict[str, str]] = None
    notes: Optional[Dict[str, str]] = None
    include_insights: bool = False   # 🔥 default OFF (fix hallucination)
    include_notes: bool = False
    max_tokens: Optional[int] = 2000
    strict_source_only: bool = True
    priority_weights: Optional[Dict[str, int]] = None

    def __post_init__(self):
        if self.sources is None:
            self.sources = {}
        if self.notes is None:
            self.notes = {}
        if self.priority_weights is None:
            self.priority_weights = {
                "source": 100,
                "insight": 70,
                "note": 50
            }


# =========================
# MAIN BUILDER
# =========================

class ContextBuilder:

    def __init__(self, **kwargs):
        self.params = kwargs

        self.source_id: Optional[str] = kwargs.get("source_id")
        self.notebook_id: Optional[str] = kwargs.get("notebook_id")

        context_config_arg = kwargs.get("context_config")

        if context_config_arg:
            self.context_config = context_config_arg
        else:
            self.context_config = ContextConfig(
                max_tokens=kwargs.get("max_tokens"),
                include_insights=kwargs.get("include_insights", False),
                include_notes=kwargs.get("include_notes", False),
            )

        self.max_tokens = self.context_config.max_tokens
        self.items: List[ContextItem] = []

        logger.info(f"[INIT] ContextBuilder params: {kwargs}")

    # =========================
    # BUILD ENTRY
    # =========================

    async def build(self) -> Dict[str, Any]:
        try:
            logger.info("🚀 Context Building Started")

            self.items = []

            # ✅ STRICT SOURCE MODE
            if self.source_id:
                logger.info(f"[MODE] Source Only: {self.source_id}")
                await self._add_source_context(self.source_id)

            elif self.notebook_id and not self.context_config.strict_source_only:
                logger.info(f"[MODE] Notebook: {self.notebook_id}")
                await self._add_notebook_context(self.notebook_id)

            else:
                logger.warning("⚠️ No valid input provided")

            # Post processing
            self.remove_duplicates()
            self.prioritize()

            if self.max_tokens:
                self.truncate_to_fit(self.max_tokens)

            response = self._format_response()

            logger.info("✅ Context Building Complete")
            logger.info(f"📊 Tokens: {response['total_tokens']} | Items: {response['total_items']}")

            return response

        except Exception as e:
            logger.error(f"❌ Build failed: {str(e)}")
            raise DatabaseOperationError(str(e))

    # =========================
    # SOURCE
    # =========================

    async def _add_source_context(self, source_id: str):
        try:
            full_source_id = (
                source_id if source_id.startswith("source:")
                else f"source:{source_id}"
            )

            source = await Source.get(full_source_id)
            if not source:
                raise NotFoundError(f"Source not found: {source_id}")

            logger.info(f"📥 Loading Source: {full_source_id}")

            source_context = await source.get_context(context_size="long")

            # Keep title and full_text - use long context to get actual document content
            if isinstance(source_context, dict):
                source_context = {
                    "title": source_context.get("title"),
                    "full_text": source_context.get("full_text", "")[:8000]  # up to 8000 chars
                }

            self.add_item(ContextItem(
                id=source.id or "",
                type="source",
                content=source_context,
                priority=100
            ))

            # ✅ Insights (optional)
            if self.context_config.include_insights:
                insights = await source.get_insights()

                logger.info(f"📌 Insights count: {len(insights)}")

                for ins in insights:
                    self.add_item(ContextItem(
                        id=ins.id or "",
                        type="insight",
                        content={
                            "insight_type": ins.insight_type,
                            "content": ins.content
                        },
                        priority=70
                    ))

        except Exception as e:
            logger.error(f"❌ Source error: {e}")

    # =========================
    # NOTEBOOK
    # =========================

    async def _add_notebook_context(self, notebook_id: str):
        try:
            notebook = await Notebook.get(notebook_id)

            if not notebook:
                raise NotFoundError(f"Notebook not found: {notebook_id}")

            sources = await notebook.get_sources()

            logger.info(f"📚 Notebook sources: {len(sources)}")

            for src in sources:
                if src.id:
                    await self._add_source_context(src.id)

            if self.context_config.include_notes:
                notes = await notebook.get_notes()

                logger.info(f"📝 Notes count: {len(notes)}")

                for note in notes:
                    if note.id:
                        await self._add_note_context(note.id)

        except Exception as e:
            logger.error(f"❌ Notebook error: {e}")

    # =========================
    # NOTES
    # =========================

    async def _add_note_context(self, note_id: str):
        try:
            full_note_id = (
                note_id if note_id.startswith("note:")
                else f"note:{note_id}"
            )

            note = await Note.get(full_note_id)

            if not note:
                return

            note_context = note.get_context(context_size="short")

            self.add_item(ContextItem(
                id=note.id or "",
                type="note",
                content=note_context,
                priority=50
            ))

        except Exception as e:
            logger.error(f"❌ Note error: {e}")

    # =========================
    # HELPERS
    # =========================

    def add_item(self, item: ContextItem):
        self.items.append(item)
        logger.debug(f"➕ {item.type} added | tokens={item.token_count}")

    def prioritize(self):
        self.items.sort(key=lambda x: x.priority, reverse=True)

    def truncate_to_fit(self, max_tokens: int):
        MAX_CONTEXT_TOKENS = 1500  # 🔥 hard cap

        total = sum(i.token_count or 0 for i in self.items)
        logger.info(f"🔢 Tokens before: {total}")

        # Hard override
        if total > MAX_CONTEXT_TOKENS:
            max_tokens = MAX_CONTEXT_TOKENS

        while total > max_tokens and self.items:
            removed = self.items.pop()
            total -= removed.token_count or 0

        logger.info(f"✂️ Tokens after: {total}")

    def remove_duplicates(self):
        seen = set()
        unique = []

        for i in self.items:
            if i.id not in seen:
                unique.append(i)
                seen.add(i.id)

        self.items = unique

    # =========================
    # RESPONSE
    # =========================

    def _format_response(self) -> Dict[str, Any]:
        sources, notes, insights = [], [], []

        for item in self.items:
            if item.type == "source":
                sources.append(item.content)
            elif item.type == "note":
                notes.append(item.content)
            elif item.type == "insight":
                insights.append(item.content)

        total_tokens = sum(i.token_count or 0 for i in self.items)

        return {
            "sources": sources,
            "notes": notes,
            "insights": insights,
            "total_tokens": total_tokens,
            "total_items": len(self.items),
            "metadata": {
                "source_count": len(sources),
                "note_count": len(notes),
                "insight_count": len(insights),
                "strict_mode": self.context_config.strict_source_only
            }
        }


# =========================
# CONVENIENCE FUNCTIONS
# =========================

async def build_source_context(source_id: str) -> Dict[str, Any]:
    builder = ContextBuilder(source_id=source_id)
    return await builder.build()


async def build_notebook_context(notebook_id: str) -> Dict[str, Any]:
    builder = ContextBuilder(
        notebook_id=notebook_id,
        context_config=ContextConfig(strict_source_only=False)
    )
    return await builder.build()


async def build_mixed_context(
    source_ids: Optional[List[str]] = None,
    note_ids: Optional[List[str]] = None,
    notebook_id: Optional[str] = None,
) -> Dict[str, Any]:

    config = ContextConfig(strict_source_only=False)

    if source_ids:
        config.sources = {sid: "full content" for sid in source_ids}

    if note_ids:
        config.notes = {nid: "full content" for nid in note_ids}

    builder = ContextBuilder(
        notebook_id=notebook_id,
        context_config=config
    )

    return await builder.build()
