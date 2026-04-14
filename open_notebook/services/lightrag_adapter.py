"""
LightRAG adapter — wraps Esperanto LLM/embedding provisioning into
LightRAG-compatible async callables.

If LightRAG is not installed, the functions still resolve without error
but should never be called (GraphService gates on import availability).
"""

from typing import Any, Callable, Coroutine

from loguru import logger


async def build_llm_func() -> Callable[..., Coroutine[Any, Any, str]]:
    """
    Build an async LLM function compatible with LightRAG's llm_model_func.

    Uses Esperanto's ModelManager to provision the default chat model,
    then wraps its invoke into the signature LightRAG expects.
    """
    from open_notebook.ai.models import model_manager

    model = await model_manager.get_default_model("chat")
    if model is None:
        raise RuntimeError(
            "No default chat model configured. "
            "Please go to Settings → Models and configure a default chat model."
        )

    async def llm_func(prompt: str, **kwargs) -> str:
        from open_notebook.utils import clean_thinking_content

        response = await model.achat_complete([{"role": "user", "content": prompt}])
        content = response.content if hasattr(response, "content") else str(response)
        return clean_thinking_content(content)

    return llm_func


async def build_embedding_func() -> Callable[..., Coroutine[Any, Any, Any]]:
    """
    Build an async embedding function compatible with LightRAG's embedding_func.

    Uses Esperanto's ModelManager to provision the default embedding model,
    then wraps its embed call into the signature LightRAG expects.
    """
    from open_notebook.ai.models import model_manager

    model = await model_manager.get_default_model("embedding")
    if model is None:
        raise RuntimeError(
            "No default embedding model configured. "
            "Please go to Settings → Models and configure a default embedding model."
        )

    async def embedding_func(texts: list[str], **kwargs) -> list[list[float]]:
        try:
            result = await model.aembed(texts)
            return result
        except Exception as error:
            logger.error(f"Embedding generation failed in LightRAG adapter: {error}")
            raise

    return embedding_func
