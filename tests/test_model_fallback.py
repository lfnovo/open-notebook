"""Tests for the fallback-chain model provisioning feature.

Covers:
- ModelManager.get_fallback_chain(): resolves configured fallback ids,
  skips ones that fail to resolve or that duplicate the primary, and
  excludes paid models once STUDY_BUDGET_USD is exhausted (free ones are
  never excluded by budget).
- provision_langchain_model(): fully backward-compatible when no fallback
  chain is configured (bare primary, unchanged), and wires
  Runnable.with_fallbacks() with usage tracking attached per-model when a
  chain is configured.
- UsageEvent.get_summary()/is_within_budget(): the GROUP ALL aggregation
  fix and the budget-cutoff helper.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from esperanto import LanguageModel

from open_notebook.ai.models import ModelManager
from open_notebook.domain.usage import UsageEvent


def make_fake_language_model(provider: str, name: str) -> MagicMock:
    """A MagicMock that passes isinstance(x, LanguageModel) via spec=."""
    fake = MagicMock(spec=LanguageModel)
    fake.provider = provider
    fake.get_model_name.return_value = name
    fake.to_langchain.return_value = MagicMock()
    fake.to_langchain.return_value.callbacks = None
    return fake


def make_defaults(**overrides) -> MagicMock:
    defaults = MagicMock()
    defaults.default_chat_model = "model:chat-primary"
    defaults.default_transformation_model = None
    defaults.default_tools_model = None
    defaults.large_context_model = None
    defaults.default_text_to_speech_model = None
    defaults.default_speech_to_text_model = None
    defaults.default_embedding_model = "model:embed"
    defaults.chat_fallback_models = []
    defaults.transformation_fallback_models = []
    defaults.large_context_fallback_models = []
    defaults.tools_fallback_models = []
    defaults.embedding_fallback_models = []
    defaults.text_to_speech_fallback_models = []
    defaults.speech_to_text_fallback_models = []
    for key, value in overrides.items():
        setattr(defaults, key, value)
    return defaults


class TestGetFallbackChain:
    @pytest.mark.asyncio
    async def test_no_fallbacks_configured_returns_empty(self):
        manager = ModelManager()
        defaults = make_defaults(chat_fallback_models=[])
        with patch.object(
            manager, "get_defaults", new=AsyncMock(return_value=defaults)
        ):
            result = await manager.get_fallback_chain("chat")
        assert result == []

    @pytest.mark.asyncio
    async def test_unknown_model_type_returns_empty(self):
        manager = ModelManager()
        result = await manager.get_fallback_chain("not_a_real_type")
        assert result == []

    @pytest.mark.asyncio
    async def test_resolves_configured_fallbacks_in_order(self):
        manager = ModelManager()
        defaults = make_defaults(
            chat_fallback_models=["model:fb1", "model:fb2"]
        )
        fb1 = make_fake_language_model("openrouter", "free-model-a:free")
        fb2 = make_fake_language_model("openrouter", "free-model-b:free")

        async def fake_get_model(model_id, **kwargs):
            return {"model:fb1": fb1, "model:fb2": fb2}[model_id]

        with (
            patch.object(
                manager, "get_defaults", new=AsyncMock(return_value=defaults)
            ),
            patch.object(manager, "get_model", side_effect=fake_get_model),
            patch(
                "open_notebook.ai.models.get_price_per_token",
                new=AsyncMock(return_value=(0.0, 0.0)),
            ),
        ):
            result = await manager.get_fallback_chain("chat")

        assert result == [fb1, fb2]

    @pytest.mark.asyncio
    async def test_broken_fallback_entry_is_skipped_not_fatal(self):
        """A deleted model / missing credential in one fallback slot must
        not break resolution of the rest of the chain."""
        manager = ModelManager()
        defaults = make_defaults(
            chat_fallback_models=["model:broken", "model:good"]
        )
        good = make_fake_language_model("openrouter", "good-model:free")

        async def fake_get_model(model_id, **kwargs):
            if model_id == "model:broken":
                raise Exception("model not found")
            return good

        with (
            patch.object(
                manager, "get_defaults", new=AsyncMock(return_value=defaults)
            ),
            patch.object(manager, "get_model", side_effect=fake_get_model),
            patch(
                "open_notebook.ai.models.get_price_per_token",
                new=AsyncMock(return_value=(0.0, 0.0)),
            ),
        ):
            result = await manager.get_fallback_chain("chat")

        assert result == [good]

    @pytest.mark.asyncio
    async def test_skips_fallback_matching_primary_provider_and_name(self):
        manager = ModelManager()
        defaults = make_defaults(chat_fallback_models=["model:same"])
        same = make_fake_language_model("openrouter", "the-primary-model")

        with (
            patch.object(
                manager, "get_defaults", new=AsyncMock(return_value=defaults)
            ),
            patch.object(manager, "get_model", new=AsyncMock(return_value=same)),
        ):
            result = await manager.get_fallback_chain(
                "chat",
                primary_provider="openrouter",
                primary_model_name="the-primary-model",
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_paid_fallback_excluded_when_over_budget(self):
        manager = ModelManager()
        defaults = make_defaults(chat_fallback_models=["model:paid"])
        paid = make_fake_language_model("openrouter", "gpt-5-mini")

        with (
            patch.object(
                manager, "get_defaults", new=AsyncMock(return_value=defaults)
            ),
            patch.object(manager, "get_model", new=AsyncMock(return_value=paid)),
            patch(
                "open_notebook.ai.models.get_price_per_token",
                new=AsyncMock(return_value=(0.000002, 0.000006)),
            ),
            patch(
                "open_notebook.domain.usage.UsageEvent.is_within_budget",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await manager.get_fallback_chain("chat")

        assert result == []

    @pytest.mark.asyncio
    async def test_paid_fallback_included_when_within_budget(self):
        manager = ModelManager()
        defaults = make_defaults(chat_fallback_models=["model:paid"])
        paid = make_fake_language_model("openrouter", "gpt-5-mini")

        with (
            patch.object(
                manager, "get_defaults", new=AsyncMock(return_value=defaults)
            ),
            patch.object(manager, "get_model", new=AsyncMock(return_value=paid)),
            patch(
                "open_notebook.ai.models.get_price_per_token",
                new=AsyncMock(return_value=(0.000002, 0.000006)),
            ),
            patch(
                "open_notebook.domain.usage.UsageEvent.is_within_budget",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = await manager.get_fallback_chain("chat")

        assert result == [paid]

    @pytest.mark.asyncio
    async def test_free_fallback_never_excluded_by_budget(self):
        """A $0 fallback must be included even when over budget - budget
        checks apply only to paid models, and the budget check itself must
        never even be invoked for a free-only chain."""
        manager = ModelManager()
        defaults = make_defaults(chat_fallback_models=["model:free"])
        free = make_fake_language_model("openrouter", "free-model:free")
        budget_check = AsyncMock(return_value=False)

        with (
            patch.object(
                manager, "get_defaults", new=AsyncMock(return_value=defaults)
            ),
            patch.object(manager, "get_model", new=AsyncMock(return_value=free)),
            patch(
                "open_notebook.ai.models.get_price_per_token",
                new=AsyncMock(return_value=(0.0, 0.0)),
            ),
            patch(
                "open_notebook.domain.usage.UsageEvent.is_within_budget",
                budget_check,
            ),
        ):
            result = await manager.get_fallback_chain("chat")

        assert result == [free]
        budget_check.assert_not_called()


class TestProvisionLangchainModelBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_no_fallbacks_configured_returns_bare_primary(self):
        """Regression check: a config with no fallback chain must behave
        exactly as before - the bare primary model, not a
        RunnableWithFallbacks wrapper."""
        from open_notebook.ai.provision import provision_langchain_model

        primary = make_fake_language_model("openrouter", "primary-model")
        primary_lc = primary.to_langchain.return_value

        with (
            patch(
                "open_notebook.ai.provision.model_manager.get_default_model",
                new=AsyncMock(return_value=primary),
            ),
            patch(
                "open_notebook.ai.provision.model_manager.get_fallback_chain",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await provision_langchain_model("hello", None, "chat")

        assert result is primary_lc

    @pytest.mark.asyncio
    async def test_fallbacks_configured_wraps_with_with_fallbacks(self):
        from open_notebook.ai.provision import provision_langchain_model

        primary = make_fake_language_model("openrouter", "primary-model")
        fallback = make_fake_language_model("openrouter", "fallback-model")

        primary_lc = primary.to_langchain.return_value
        fallback_lc = fallback.to_langchain.return_value
        wrapped = MagicMock(name="RunnableWithFallbacks")
        primary_lc.with_fallbacks.return_value = wrapped

        with (
            patch(
                "open_notebook.ai.provision.model_manager.get_default_model",
                new=AsyncMock(return_value=primary),
            ),
            patch(
                "open_notebook.ai.provision.model_manager.get_fallback_chain",
                new=AsyncMock(return_value=[fallback]),
            ),
        ):
            result = await provision_langchain_model("hello", None, "chat")

        assert result is wrapped
        primary_lc.with_fallbacks.assert_called_once_with([fallback_lc])
        # Usage tracking attached to BOTH the primary and the fallback
        # individually (not only the combined runnable) so cost/tokens are
        # attributed correctly regardless of which one actually serves the
        # request.
        assert primary_lc.callbacks and len(primary_lc.callbacks) == 1
        assert fallback_lc.callbacks and len(fallback_lc.callbacks) == 1


class TestUsageEventBudget:
    @pytest.mark.asyncio
    async def test_get_summary_totals_query_uses_group_all(self):
        """Regression test for the aggregation bug: the totals query must
        include GROUP ALL, or SurrealDB's math::sum() errors per-row instead
        of aggregating (silently caught, totals stayed 0 despite correct
        underlying usage_event rows)."""
        with patch(
            "open_notebook.domain.usage.repo_query", new=AsyncMock()
        ) as mock_query:
            mock_query.side_effect = [
                [{"total_cost_usd": 0.0028, "input_tokens": 970, "output_tokens": 1793}],
                [{"task_type": "chat", "cost": 0.0028}],
            ]
            since = datetime.now(timezone.utc)
            result = await UsageEvent.get_summary(since)

        totals_call = mock_query.await_args_list[0]
        assert "GROUP ALL" in totals_call.args[0]
        assert result["total_cost_usd"] == 0.0028
        assert result["input_tokens"] == 970
        assert result["output_tokens"] == 1793

    @pytest.mark.asyncio
    async def test_is_within_budget_true_when_under(self, monkeypatch):
        monkeypatch.setenv("STUDY_BUDGET_USD", "10")
        with patch.object(
            UsageEvent, "get_current_spend_usd", new=AsyncMock(return_value=2.5)
        ):
            assert await UsageEvent.is_within_budget() is True

    @pytest.mark.asyncio
    async def test_is_within_budget_false_when_at_or_over(self, monkeypatch):
        monkeypatch.setenv("STUDY_BUDGET_USD", "10")
        with patch.object(
            UsageEvent, "get_current_spend_usd", new=AsyncMock(return_value=10.0)
        ):
            assert await UsageEvent.is_within_budget() is False

    @pytest.mark.asyncio
    async def test_is_within_budget_fails_closed_on_error(self):
        """A broken budget check must never silently allow paid-fallback
        spend to run away - failure is treated as over-budget."""
        with patch.object(
            UsageEvent,
            "get_current_spend_usd",
            new=AsyncMock(side_effect=RuntimeError("db down")),
        ):
            assert await UsageEvent.is_within_budget() is False
