"""Tests for _get_preferred_model and MODEL_PREFERENCES / EMBEDDING_PREFERENCES."""

from api.routers.models import (
    EMBEDDING_PREFERENCES,
    MODEL_PREFERENCES,
    _get_preferred_model,
)


def _model(name: str, provider: str, model_id: str | None = None) -> dict:
    return {"name": name, "provider": provider, "id": model_id or f"model:{name}"}


PROVIDER_PRIORITY = ["openai", "anthropic", "google", "mistral", "groq"]


class TestGetPreferredModelOpenAI:
    def test_prefers_gpt5_over_gpt4o_mini(self):
        """gpt-5 should beat gpt-4o-mini when both are registered."""
        models = [
            _model("gpt-4o-mini", "openai"),
            _model("gpt-5", "openai"),
        ]
        result = _get_preferred_model(models, PROVIDER_PRIORITY, MODEL_PREFERENCES)
        assert result is not None
        assert result["name"] == "gpt-5"

    def test_prefers_gpt5_mini_over_gpt5(self):
        """gpt-5-mini is listed before gpt-5 so it wins as the recommended default."""
        models = [
            _model("gpt-5", "openai"),
            _model("gpt-5-mini", "openai"),
        ]
        result = _get_preferred_model(models, PROVIDER_PRIORITY, MODEL_PREFERENCES)
        assert result is not None
        assert result["name"] == "gpt-5-mini"

    def test_falls_back_to_gpt4o_when_no_gpt5(self):
        """With no gpt-5 family present, gpt-4o-mini should still win over gpt-4o."""
        models = [
            _model("gpt-4o", "openai"),
            _model("gpt-4o-mini", "openai"),
        ]
        result = _get_preferred_model(models, PROVIDER_PRIORITY, MODEL_PREFERENCES)
        assert result is not None
        assert result["name"] == "gpt-4o-mini"


class TestGetPreferredModelAnthropic:
    def test_picks_claude_sonnet_regardless_of_list_order(self):
        """Anthropic preference should match current model names like claude-sonnet-4-5."""
        models = [
            _model("claude-haiku-4-5-20251001", "anthropic"),
            _model("claude-sonnet-4-6", "anthropic"),
        ]
        result = _get_preferred_model(models, PROVIDER_PRIORITY, MODEL_PREFERENCES)
        assert result is not None
        assert "sonnet" in result["name"].lower()

    def test_picks_haiku_when_no_sonnet(self):
        """Falls back to haiku when no sonnet model is registered."""
        models = [
            _model("claude-haiku-4-5-20251001", "anthropic"),
            _model("claude-opus-4", "anthropic"),
        ]
        result = _get_preferred_model(models, PROVIDER_PRIORITY, MODEL_PREFERENCES)
        assert result is not None
        # sonnet absent → haiku beats opus (haiku listed before opus in preferences)
        assert "haiku" in result["name"].lower()

    def test_reversed_list_same_result(self):
        """Order of the input list must not determine the winner."""
        models_forward = [
            _model("claude-haiku-4-5-20251001", "anthropic"),
            _model("claude-sonnet-4-6", "anthropic"),
        ]
        models_reversed = list(reversed(models_forward))
        r1 = _get_preferred_model(models_forward, PROVIDER_PRIORITY, MODEL_PREFERENCES)
        r2 = _get_preferred_model(models_reversed, PROVIDER_PRIORITY, MODEL_PREFERENCES)
        assert r1 is not None and r2 is not None
        assert r1["name"] == r2["name"]


class TestGetPreferredModelEmbedding:
    def test_embedding_prefers_text_embedding_3_small(self):
        """Embedding slot should pick text-embedding-3-small over a chat model."""
        models = [
            _model("gpt-4o", "openai"),
            _model("text-embedding-3-small", "openai"),
            _model("text-embedding-3-large", "openai"),
        ]
        result = _get_preferred_model(models, PROVIDER_PRIORITY, EMBEDDING_PREFERENCES)
        assert result is not None
        assert result["name"] == "text-embedding-3-small"

    def test_embedding_falls_back_to_large_when_small_absent(self):
        models = [
            _model("text-embedding-3-large", "openai"),
            _model("gpt-4o", "openai"),
        ]
        result = _get_preferred_model(models, PROVIDER_PRIORITY, EMBEDDING_PREFERENCES)
        assert result is not None
        assert result["name"] == "text-embedding-3-large"


class TestGetPreferredModelEdgeCases:
    def test_empty_list_returns_none(self):
        assert _get_preferred_model([], PROVIDER_PRIORITY, MODEL_PREFERENCES) is None

    def test_unknown_provider_falls_back_to_first(self):
        """A provider not in PROVIDER_PRIORITY returns the first model as fallback."""
        models = [_model("some-model", "unknown_provider")]
        result = _get_preferred_model(models, PROVIDER_PRIORITY, MODEL_PREFERENCES)
        assert result is not None
        assert result["name"] == "some-model"
