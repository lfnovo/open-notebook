"""Research Gateway AI 适配器（SPK-03）。

嵌入式作用域下，所有 LLM 生成固定绑定 RDLens Research Gateway 的
OpenAI 兼容端点（REQ-DIS-02 的 Fork 侧边界）：
- 不经过 Open Notebook Provider/模型注册表（model_manager）；
- 客户端指定的 model_id 无效；
- RD_AI_GATEWAY_URL 未配置时 fail-closed（ConfigurationError），
  不允许落到任意用户配置的 Provider。

Gateway 的鉴权/转发契约（Research Token 注入、引擎路由）由 RDLens 侧
（FND-06 / ENG-01）定义；本适配器只负责把调用端点钉死。
"""

from langchain_openai import ChatOpenAI

from open_notebook import config
from open_notebook.exceptions import ConfigurationError

# Gateway 未指定模型名时的占位值；实际路由由 Gateway 决定
DEFAULT_GATEWAY_MODEL = "rdlens-research-engine"


def gateway_chat_model() -> ChatOpenAI:
    """返回绑定 Research Gateway 的 ChatOpenAI；未配置端点时 fail-closed。"""
    if not config.RD_AI_GATEWAY_URL:
        raise ConfigurationError(
            "RD_AI_GATEWAY_URL is required in RDLens embedded scope; "
            "all AI generation must go through the RDLens Research Gateway"
        )
    return ChatOpenAI(
        model=config.RD_AI_GATEWAY_MODEL or DEFAULT_GATEWAY_MODEL,
        base_url=config.RD_AI_GATEWAY_URL,
        api_key=config.RD_AI_GATEWAY_API_KEY or "rdlens-embedded",
    )
