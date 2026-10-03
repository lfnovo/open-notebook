"""
Unit tests for the Ask graph (open_notebook.graphs.ask).

Covers the output token budget shared by the three model stages and the
handling of empty strategies / empty partial answers produced by reasoning
models that exhaust their budget while thinking (#1221).
"""

import json
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from open_notebook.exceptions import ExternalServiceError
from open_notebook.graphs.ask import (
    ASK_MAX_TOKENS,
    Search,
    Strategy,
    ThreadState,
    call_model_with_messages,
    provide_answer,
    trigger_queries,
    write_final_answer,
)

EMPTY_CONFIG = cast(RunnableConfig, {"configurable": {}})


def _model_returning(content: str) -> MagicMock:
    model = MagicMock()
    model.ainvoke = AsyncMock(return_value=MagicMock(content=content))
    return model


def _strategy_json(terms: list[str]) -> str:
    return json.dumps(
        {
            "reasoning": "look things up",
            "searches": [{"term": t, "instructions": "extract"} for t in terms],
        }
    )


class TestAskTokenBudget:
    def test_budget_matches_other_workflows(self):
        """Ask uses the same 8192 budget as chat and transformations."""
        assert ASK_MAX_TOKENS == 8192

    @pytest.mark.asyncio
    async def test_strategy_stage_uses_shared_budget(self):
        state = cast(ThreadState, {"question": "q"})
        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=AsyncMock(return_value=_model_returning(_strategy_json(["rag"]))),
        ) as provision:
            await call_model_with_messages(state, EMPTY_CONFIG)
        assert provision.call_args.kwargs["max_tokens"] == ASK_MAX_TOKENS

    @pytest.mark.asyncio
    async def test_answer_stage_uses_shared_budget(self):
        state = {"question": "q", "term": "rag", "instructions": "extract"}
        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                new=AsyncMock(return_value=[{"id": "source:1", "content": "x"}]),
            ),
            patch(
                "open_notebook.graphs.ask.provision_langchain_model",
                new=AsyncMock(return_value=_model_returning("partial")),
            ) as provision,
        ):
            await provide_answer(state, EMPTY_CONFIG)  # type: ignore[arg-type]
        assert provision.call_args.kwargs["max_tokens"] == ASK_MAX_TOKENS

    @pytest.mark.asyncio
    async def test_final_stage_uses_shared_budget(self):
        state = cast(
            ThreadState,
            {
                "question": "q",
                "strategy": Strategy(reasoning="r", searches=[]),
                "answers": ["a"],
            },
        )
        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=AsyncMock(return_value=_model_returning("final")),
        ) as provision:
            result = await write_final_answer(state, EMPTY_CONFIG)
        assert provision.call_args.kwargs["max_tokens"] == ASK_MAX_TOKENS
        assert result == {"final_answer": "final"}


class TestEmptyStrategyHandling:
    @pytest.mark.asyncio
    async def test_blank_search_terms_are_dropped(self):
        state = cast(ThreadState, {"question": "q"})
        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=AsyncMock(
                return_value=_model_returning(_strategy_json(["", "  ", "rag"]))
            ),
        ):
            result = await call_model_with_messages(state, EMPTY_CONFIG)
        assert [s.term for s in result["strategy"].searches] == ["rag"]

    @pytest.mark.asyncio
    async def test_all_blank_terms_raise_instead_of_silent_no_results(self):
        state = cast(ThreadState, {"question": "q"})
        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=AsyncMock(return_value=_model_returning(_strategy_json(["", "", ""]))),
        ):
            with pytest.raises(ExternalServiceError, match="no search terms"):
                await call_model_with_messages(state, EMPTY_CONFIG)

    @pytest.mark.asyncio
    async def test_no_searches_raise(self):
        state = cast(ThreadState, {"question": "q"})
        with patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=AsyncMock(return_value=_model_returning(_strategy_json([]))),
        ):
            with pytest.raises(ExternalServiceError):
                await call_model_with_messages(state, EMPTY_CONFIG)

    @pytest.mark.asyncio
    async def test_thinking_only_partial_answer_is_skipped(self):
        state = {"question": "q", "term": "rag", "instructions": "extract"}
        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                new=AsyncMock(return_value=[{"id": "source:1", "content": "x"}]),
            ),
            patch(
                "open_notebook.graphs.ask.provision_langchain_model",
                new=AsyncMock(
                    return_value=_model_returning("<think>only reasoning</think>")
                ),
            ),
        ):
            result = await provide_answer(state, EMPTY_CONFIG)  # type: ignore[arg-type]
        assert result == {"answers": []}

    @pytest.mark.asyncio
    async def test_truncated_thinking_partial_answer_is_skipped(self):
        """Budget exhausted inside <think> must not leak reasoning as an answer."""
        state = {"question": "q", "term": "rag", "instructions": "extract"}
        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                new=AsyncMock(return_value=[{"id": "source:1", "content": "x"}]),
            ),
            patch(
                "open_notebook.graphs.ask.provision_langchain_model",
                new=AsyncMock(return_value=_model_returning("<think>cut off mid")),
            ),
        ):
            result = await provide_answer(state, EMPTY_CONFIG)  # type: ignore[arg-type]
        assert result == {"answers": []}

    def test_search_model_accepts_blank_term(self):
        """The filter, not the schema, is responsible for blank terms."""
        assert Search(term="", instructions="x").term == ""


class TestNotebookScope:
    """The notebook scope travels from the thread state into every search (#574, #87)."""

    @pytest.mark.asyncio
    async def test_trigger_queries_forwards_scope_to_each_search(self):
        state = cast(
            ThreadState,
            {
                "question": "q",
                "notebook_ids": ["notebook:a"],
                "strategy": Strategy(
                    reasoning="r",
                    searches=[
                        Search(term="one", instructions="x"),
                        Search(term="two", instructions="y"),
                    ],
                ),
            },
        )
        sends = await trigger_queries(state, EMPTY_CONFIG)
        assert [s.arg["notebook_ids"] for s in sends] == [
            ["notebook:a"],
            ["notebook:a"],
        ]

    @pytest.mark.asyncio
    async def test_trigger_queries_defaults_to_global_scope(self):
        state = cast(
            ThreadState,
            {
                "question": "q",
                "strategy": Strategy(
                    reasoning="r", searches=[Search(term="one", instructions="x")]
                ),
            },
        )
        sends = await trigger_queries(state, EMPTY_CONFIG)
        assert sends[0].arg["notebook_ids"] == []

    @pytest.mark.asyncio
    async def test_provide_answer_scopes_vector_search(self):
        state = {
            "question": "q",
            "term": "rag",
            "instructions": "extract",
            "notebook_ids": ["notebook:a"],
        }
        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                new=AsyncMock(return_value=[{"id": "source:1", "content": "x"}]),
            ) as search,
            patch(
                "open_notebook.graphs.ask.provision_langchain_model",
                new=AsyncMock(return_value=_model_returning("partial")),
            ),
        ):
            await provide_answer(state, EMPTY_CONFIG)  # type: ignore[arg-type]
        assert search.await_args is not None
        assert search.await_args.kwargs["notebook_ids"] == ["notebook:a"]

    @pytest.mark.asyncio
    async def test_provide_answer_without_scope_searches_globally(self):
        state = {"question": "q", "term": "rag", "instructions": "extract"}
        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                new=AsyncMock(return_value=[]),
            ) as search,
        ):
            await provide_answer(state, EMPTY_CONFIG)  # type: ignore[arg-type]
        assert search.await_args is not None
        assert search.await_args.kwargs["notebook_ids"] is None
