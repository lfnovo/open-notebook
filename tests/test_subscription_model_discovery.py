import pytest

from api import subscription_model_discovery as discovery


def test_parse_chatgpt_models_only_returns_picker_visible_models():
    payload = {
        "models": [
            {
                "slug": "gpt-current",
                "display_name": "GPT Current",
                "description": "Recommended",
                "visibility": "list",
            },
            {"slug": "internal-review", "visibility": "hide"},
            {"slug": "gpt-current", "visibility": "list"},
        ]
    }

    assert discovery._parse_chatgpt_models(payload) == [
        {
            "name": "gpt-current",
            "description": "GPT Current — Recommended",
        }
    ]


def test_parse_claude_models_only_returns_claude_code_subscription_models():
    payload = {
        "surfaces": {
            "cc": {
                "model_selector_config": [
                    {
                        "id": "cc",
                        "models": [
                            {
                                "id": "claude-current",
                                "name": "Claude Current",
                                "description": "Everyday model",
                                "offered_on": ["first_party", "bedrock"],
                            },
                            {
                                "id": "claude-bedrock-only",
                                "offered_on": ["bedrock"],
                            },
                        ],
                    }
                ]
            }
        }
    }

    assert discovery._parse_claude_models(payload) == [
        {
            "name": "claude-current",
            "description": "Claude Current — Everyday model",
        }
    ]


@pytest.mark.asyncio
async def test_chatgpt_discovery_uses_authenticated_subscription_catalog(monkeypatch):
    class Credential:
        id = "credential:test"
        account_id = "account-test"

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "models": [
                    {
                        "slug": "gpt-live",
                        "display_name": "GPT Live",
                        "visibility": "list",
                    }
                ]
            }

    captured = {}

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, headers=None):
            captured.update(url=url, params=params, headers=headers)
            return Response()

    async def _token(_credential):
        return "test-token"

    monkeypatch.setattr(discovery, "get_valid_access_token", _token)
    monkeypatch.setattr(discovery.httpx, "AsyncClient", Client)
    monkeypatch.setattr(discovery, "_client_version", lambda: "1.2.3")

    models = await discovery._discover_chatgpt_models(Credential())

    assert models == [{"name": "gpt-live", "description": "GPT Live"}]
    assert captured["url"] == discovery.CHATGPT_MODELS_URL
    assert captured["params"] == {"client_version": "1.2.3"}
    assert captured["headers"]["authorization"] == "Bearer test-token"
    assert captured["headers"]["chatgpt-account-id"] == "account-test"


@pytest.mark.asyncio
async def test_failed_refresh_reuses_last_successful_dynamic_catalog(monkeypatch):
    class Credential:
        id = "credential:cached"
        subscription_kind = "claude"

    live_models = [{"name": "claude-live"}]

    async def _success():
        return live_models

    async def _failure():
        raise RuntimeError("catalog unavailable")

    discovery._last_successful_models.clear()
    monkeypatch.setattr(discovery, "_discover_claude_models", _success)
    assert await discovery.discover_subscription_models(Credential()) == live_models

    monkeypatch.setattr(discovery, "_discover_claude_models", _failure)
    assert await discovery.discover_subscription_models(Credential()) == live_models
