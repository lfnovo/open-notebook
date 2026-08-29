"""
Tests for commands/ask_sources_command.py::_select_model_within_run_budget.

This is the pre-flight model-selection gate for the "ask across sources"
command: it must always accept a free model outright, accept a paid model
only when the *estimated* cost for the given input token count stays under
MAX_COST_PER_RUN_USD ($0.30), and raise ValueError when nothing configured
fits - never silently proceed with an unbounded-cost call.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from commands.ask_sources_command import (
    MAX_COST_PER_RUN_USD,
    _select_model_within_run_budget,
)


def _fake_model(provider: str, name: str) -> SimpleNamespace:
    return SimpleNamespace(provider=provider, get_model_name=lambda: name)


# isinstance(candidate, LanguageModel) would reject these lightweight fakes -
# patched to `object` for these tests so the price/budget logic under test
# is exercised without needing a real esperanto LanguageModel instance.
@pytest.fixture(autouse=True)
def _allow_fake_models():
    with patch("commands.ask_sources_command.LanguageModel", object):
        yield


class TestSelectModelWithinRunBudget:
    @pytest.mark.asyncio
    async def test_free_default_model_is_always_accepted(self):
        free_model = _fake_model("openrouter", "nvidia/nemotron-3-ultra:free")
        with (
            patch(
                "commands.ask_sources_command.model_manager.get_default_model",
                new=AsyncMock(return_value=free_model),
            ),
            patch(
                "commands.ask_sources_command.model_manager.get_fallback_chain",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "commands.ask_sources_command.get_price_per_token",
                new=AsyncMock(return_value=(0.0, 0.0)),
            ),
        ):
            model, provider, name, cost = await _select_model_within_run_budget(
                900_000  # a whole book - must not matter for a free model
            )

        assert model is free_model
        assert provider == "openrouter"
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_paid_fallback_within_budget_is_accepted(self):
        # Default model fails to resolve; the one fallback is paid but cheap
        # enough for this amount of content to stay under $0.30.
        paid_model = _fake_model("openrouter", "deepseek/deepseek-v3.2")
        with (
            patch(
                "commands.ask_sources_command.model_manager.get_default_model",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "commands.ask_sources_command.model_manager.get_fallback_chain",
                new=AsyncMock(return_value=[paid_model]),
            ),
            patch(
                "commands.ask_sources_command.get_price_per_token",
                new=AsyncMock(return_value=(0.000000269, 0.0000004)),
            ),
        ):
            model, provider, name, cost = await _select_model_within_run_budget(10_000)

        assert model is paid_model
        assert 0 < cost < MAX_COST_PER_RUN_USD

    @pytest.mark.asyncio
    async def test_paid_model_over_budget_is_skipped_for_a_cheaper_one(self):
        expensive_model = _fake_model("openrouter", "openai/gpt-5.2-pro")
        cheap_model = _fake_model("openrouter", "openai/gpt-5-nano")

        prices = {
            "openai/gpt-5.2-pro": (0.00003, 0.00006),  # far too expensive for 900k tokens
            "openai/gpt-5-nano": (0.00000005, 0.0000004),
        }

        async def fake_price(provider, name):
            return prices[name]

        with (
            patch(
                "commands.ask_sources_command.model_manager.get_default_model",
                new=AsyncMock(return_value=expensive_model),
            ),
            patch(
                "commands.ask_sources_command.model_manager.get_fallback_chain",
                new=AsyncMock(return_value=[cheap_model]),
            ),
            patch(
                "commands.ask_sources_command.get_price_per_token",
                new=fake_price,
            ),
        ):
            model, provider, name, cost = await _select_model_within_run_budget(900_000)

        assert model is cheap_model
        assert cost < MAX_COST_PER_RUN_USD

    @pytest.mark.asyncio
    async def test_raises_when_nothing_fits_the_budget(self):
        expensive_model = _fake_model("openrouter", "openai/gpt-5.2-pro")
        with (
            patch(
                "commands.ask_sources_command.model_manager.get_default_model",
                new=AsyncMock(return_value=expensive_model),
            ),
            patch(
                "commands.ask_sources_command.model_manager.get_fallback_chain",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "commands.ask_sources_command.get_price_per_token",
                new=AsyncMock(return_value=(0.00003, 0.00006)),
            ),
            pytest.raises(ValueError, match="0.30"),
        ):
            await _select_model_within_run_budget(900_000)
