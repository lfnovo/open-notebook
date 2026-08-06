"""
RDLens 嵌入式作用域禁用探针（SPK-03 / Issue #19）— Red 测试。

在内部 Fork 证明嵌入式模式（RD_EMBEDDED_MODE=1）下的禁用边界：
- REQ-DIS-01：保存 Source/Note 后无 embed_note / source_embedding（vectorize）
- REQ-DIS-02：原生 Provider 路径禁用，LLM 固定绑定 Research Gateway；
             词法搜索失败不回落向量搜索
- REQ-DIS-03：Transformation 仅 prompt-only，无代码/工具/URL/市场字段
- REQ-SCOPE-03：全局 Notebook、认证、系统设置、Provider/凭据、媒体、
             直接上传/URL 来源被屏蔽
- REQ-AUTH-03：客户端不能获取或切换非固定 Notebook ID

Red 阶段（基准 30c7e2a6，无任何嵌入式能力）：
- 域层测试因产品代码未检查嵌入式标志而失败（embed_note/vectorize 仍被提交、
  Provider 仍走 model_manager、词法失败仍回退向量）；
- API 屏蔽矩阵测试因 api.embedded_scope 模块缺失以 ImportError 失败。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.domain.notebook import Note, Source, text_search
from open_notebook.exceptions import InvalidInputError

GATEWAY_URL = "http://gateway.internal/v1"
GATEWAY_MODEL = "rdlens-research-engine"


def _embedded(monkeypatch, **overrides):
    """开启嵌入式作用域配置（open_notebook.config 模块属性，调用时读取）。"""
    defaults = {
        "RD_EMBEDDED_MODE": True,
        "RD_EMBEDDED_NOTEBOOK_ID": "notebook:42",
        "RD_AI_GATEWAY_URL": GATEWAY_URL,
        "RD_AI_GATEWAY_MODEL": GATEWAY_MODEL,
        "RD_AI_GATEWAY_API_KEY": "",
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        monkeypatch.setattr(f"open_notebook.config.{key}", value, raising=False)


class TestEmbeddingDisabled:
    """REQ-DIS-01：保存 Source/Note 后无 Embedding 任务或记录。"""

    @pytest.mark.asyncio
    async def test_note_save_skips_embed_note_in_embedded_mode(self, monkeypatch):
        _embedded(monkeypatch)
        note = Note(title="Test", content="some content")
        with (
            patch("open_notebook.domain.base.ObjectModel.save", new=AsyncMock()),
            patch(
                "open_notebook.domain.notebook.submit_command", new=AsyncMock()
            ) as mock_submit,
        ):
            object.__setattr__(note, "id", "note:abc123")
            command_id = await note.save()

        assert command_id is None
        mock_submit.assert_not_called()

    @pytest.mark.asyncio
    async def test_note_save_still_saves_durably_in_embedded_mode(self, monkeypatch):
        """Note 本体必须照常保存（Gateway 读路径依赖），仅禁止 Embedding。"""
        _embedded(monkeypatch)
        note = Note(title="Test", content="some content")
        with (
            patch(
                "open_notebook.domain.base.ObjectModel.save", new=AsyncMock()
            ) as mock_super_save,
            patch("open_notebook.domain.notebook.submit_command", new=AsyncMock()),
        ):
            object.__setattr__(note, "id", "note:abc123")
            await note.save()

        mock_super_save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_source_vectorize_rejected_in_embedded_mode(self, monkeypatch):
        _embedded(monkeypatch)
        source = Source(id="source:test_valid", title="Test", full_text="Real content")
        with patch("open_notebook.domain.notebook.submit_command", new=AsyncMock()) as mock_submit:
            with pytest.raises(InvalidInputError):
                await source.vectorize()
        mock_submit.assert_not_called()

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    async def test_save_source_skips_vectorize_in_embedded_mode(self, mock_get, monkeypatch):
        _embedded(monkeypatch)
        from content_core.common import ExtractionOutput
        from typing import cast

        from open_notebook.graphs.source import SourceState, save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = None
        mock_source.full_text = "Some content"
        mock_source.save = AsyncMock()
        mock_source.vectorize = AsyncMock()
        mock_get.return_value = mock_source

        state = {
            "source_id": "source:123",
            "content_state": {"url": None, "file_path": None},
            "extraction": ExtractionOutput(title="", content="Some content"),
            "embed": True,
            "apply_transformations": [],
        }

        await save_source(cast(SourceState, state))

        mock_source.save.assert_awaited_once()
        mock_source.vectorize.assert_not_awaited()


class TestNativeAIBlocked:
    """REQ-DIS-02：Provider 路径禁用，LLM 只走 Research Gateway。"""

    @pytest.mark.asyncio
    async def test_provision_binds_gateway_and_skips_model_manager(self, monkeypatch):
        _embedded(monkeypatch)
        from open_notebook.ai.provision import provision_langchain_model

        with patch(
            "open_notebook.ai.provision.model_manager.get_default_model",
            new=AsyncMock(return_value=object()),
        ) as mock_mgr:
            model = await provision_langchain_model("hello", None, "transformation")

        assert model.openai_api_base == GATEWAY_URL
        assert model.model_name == GATEWAY_MODEL
        mock_mgr.assert_not_called()

    @pytest.mark.asyncio
    async def test_provision_ignores_user_model_id_in_embedded_mode(self, monkeypatch):
        """客户端指定的 model_id 在嵌入式模式下无效（REQ-DIS-02）。"""
        _embedded(monkeypatch)
        from open_notebook.ai.provision import provision_langchain_model

        with patch(
            "open_notebook.ai.provision.model_manager.get_model",
            new=AsyncMock(),
        ) as mock_get_model:
            model = await provision_langchain_model("hello", "model:user-picked", "transformation")

        assert model.openai_api_base == GATEWAY_URL
        mock_get_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_provision_fails_closed_without_gateway_url(self, monkeypatch):
        """未配置 Gateway 端点时 fail-closed，不得落到任意 Provider。"""
        _embedded(monkeypatch, RD_AI_GATEWAY_URL="")
        from open_notebook.ai.provision import provision_langchain_model
        from open_notebook.exceptions import ConfigurationError

        with patch(
            "open_notebook.ai.provision.model_manager.get_default_model",
            new=AsyncMock(return_value=object()),
        ):
            with pytest.raises(ConfigurationError):
                await provision_langchain_model("hello", None, "transformation")

    @pytest.mark.asyncio
    async def test_text_search_no_vector_fallback_in_embedded_mode(self, monkeypatch):
        """词法搜索失败不得回退向量搜索（REQ-DIS-02）。"""
        _embedded(monkeypatch)
        from open_notebook.exceptions import DatabaseOperationError

        with (
            patch(
                "open_notebook.domain.notebook.repo_query",
                side_effect=RuntimeError("position overflow"),
            ),
            patch(
                "open_notebook.domain.notebook.vector_search",
                new=AsyncMock(return_value=[{"id": "v"}]),
            ) as mock_vector,
        ):
            with pytest.raises(DatabaseOperationError):
                await text_search("keyword", 10)

        mock_vector.assert_not_called()


class TestAPISurfaceBlocked:
    """REQ-SCOPE-03 / REQ-AUTH-03 / REQ-DIS-01/02：全局页面与直接 API 屏蔽矩阵。"""

    def test_is_blocked_passthrough_by_default(self):
        from api.embedded_scope import is_blocked  # ImportError until Green

        assert is_blocked("GET", "/api/notebooks") is False
        assert is_blocked("POST", "/api/chat") is False

    def test_is_blocked_embedded_matrix(self, monkeypatch):
        _embedded(monkeypatch)
        from api.embedded_scope import is_blocked

        blocked = [
            ("GET", "/api/notebooks"),  # 全局 Notebook 列表（REQ-SCOPE-03）
            ("POST", "/api/notebooks"),  # 创建 Notebook
            ("GET", "/api/notebooks/notebook:99"),  # 非固定 Notebook（REQ-AUTH-03）
            ("PUT", "/api/notebooks/notebook:42"),  # 改写固定 Notebook
            ("DELETE", "/api/notebooks/notebook:42"),
            ("GET", "/api/recently-viewed"),
            ("POST", "/api/sources"),  # 直接上传/URL 来源（REQ-SCOPE-03）
            ("GET", "/api/auth/status"),  # 认证（REQ-SCOPE-03）
            ("GET", "/api/credentials"),  # Provider 凭据
            ("GET", "/api/providers"),  # Provider 配置
            ("GET", "/api/models"),  # 模型注册表
            ("GET", "/api/config"),
            ("GET", "/api/settings"),  # 系统设置（REQ-SCOPE-03）
            ("PUT", "/api/settings"),
            ("POST", "/api/embed"),  # REQ-DIS-01 显式 Embedding
            ("POST", "/api/embed/rebuild"),
            ("POST", "/api/chat"),  # REQ-DIS-02 原生 AI 路径
            ("POST", "/api/search"),
            ("POST", "/api/search/ask"),
            ("POST", "/api/search/ask/simple"),
            ("POST", "/api/source-chat"),
            ("GET", "/api/podcasts"),  # 媒体（REQ-SCOPE-03）
            ("GET", "/api/episode-profiles"),
            ("GET", "/api/speaker-profiles"),
            ("GET", "/api/languages"),
        ]
        allowed = [
            ("GET", "/api/notebooks/notebook:42"),  # 固定 Notebook（REQ-AUTH-03）
            ("GET", "/api/sources"),  # 来源只读（Gateway 代理）
            ("GET", "/api/sources/source:1"),
            ("GET", "/api/notes"),  # 研究产物 CRUD（Gateway 代理）
            ("POST", "/api/notes"),
            ("GET", "/api/insights"),
            ("GET", "/api/transformations"),
            ("GET", "/api/capabilities"),
            ("GET", "/health"),
        ]
        for method, path in blocked:
            assert is_blocked(method, path) is True, f"{method} {path} should be blocked"
        for method, path in allowed:
            assert is_blocked(method, path) is False, f"{method} {path} should be allowed"

    def test_embedded_mode_returns_403_on_global_api(self, monkeypatch):
        _embedded(monkeypatch)
        from fastapi.testclient import TestClient

        from api.main import app

        client = TestClient(app)
        response = client.get("/api/notebooks")
        assert response.status_code == 403


class TestTransformationPromptOnly:
    """REQ-DIS-03：Transformation 仅 prompt-only，无代码/工具/URL/市场字段。"""

    def test_transformation_schema_is_prompt_only(self):
        from api.models import TransformationCreate
        from open_notebook.domain.transformation import Transformation

        # 禁止代码、工具、外部 URL 与共享市场字段（含 ObjectModel 基础字段之外）
        forbidden = {"code", "tool", "tools", "url", "share", "marketplace", "public"}
        assert not (set(Transformation.model_fields) & forbidden)
        assert not (set(TransformationCreate.model_fields) & forbidden)
