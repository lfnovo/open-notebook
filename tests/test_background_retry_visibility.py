"""Background LLM and embedding retries must be visible in normal worker logs."""

import pytest
from loguru import logger
from surreal_commands.core.registry import registry
from surreal_commands.core.retry import build_async_retry_instance

import commands  # noqa: F401 -- import registers the @command decorators

VISIBLE_RETRY_COMMANDS = [
    "open_notebook.run_transformation",
    "open_notebook.embed_note",
    "open_notebook.embed_insight",
    "open_notebook.embed_source",
    "open_notebook.create_insight",
]


def _retry_config(command_id: str):
    item = registry.get_command_by_id(command_id)
    assert item is not None, f"{command_id} is not registered"
    assert item.retry_config is not None, f"{command_id} has no retry config"
    return item.retry_config


@pytest.mark.parametrize("command_id", VISIBLE_RETRY_COMMANDS)
def test_background_retry_is_logged_at_warning(command_id):
    assert _retry_config(command_id).retry_log_level.value == "warning"


@pytest.mark.asyncio
async def test_retry_warning_includes_attempt_error_and_delay():
    config = _retry_config("open_notebook.run_transformation").model_copy(
        update={
            "max_attempts": 2,
            "wait_strategy": "fixed",
            "wait_time": 0,
            "wait_min": 0,
            "wait_max": 0,
        }
    )
    messages: list[str] = []
    sink_id = logger.add(lambda message: messages.append(str(message)), level="WARNING")

    try:
        with pytest.raises(ConnectionError):
            async for attempt in build_async_retry_instance(config):
                with attempt:
                    raise ConnectionError("provider temporarily unavailable")
    finally:
        logger.remove(sink_id)

    assert len(messages) == 1
    assert "[Retry] Attempt 1 failed with ConnectionError" in messages[0]
    assert "provider temporarily unavailable" in messages[0]
    assert "waiting 0.0s before retry 2" in messages[0]
