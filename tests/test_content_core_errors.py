"""content-core >= 2.2 raises typed extraction errors (#1433).

content_process turns each into a user-facing ValueError, which is in
process_source's stop_on, so the job fails once instead of retrying 15 times.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import content_core as cc
import pytest

from open_notebook.graphs import source as source_graph

YOUTUBE = "https://www.youtube.com/watch?v=abc123"
PAGE = "https://example.com/article"


async def _run(state, extract):
    settings = SimpleNamespace(
        youtube_preferred_languages=None,
        default_content_processing_engine_url=None,
        default_content_processing_engine_doc=None,
        docling_ocr=None,
        docling_formulas=None,
        docling_vision=None,
    )
    with (
        patch.object(
            source_graph.ContentSettings,
            "get_instance",
            new=AsyncMock(return_value=settings),
        ),
        patch.object(
            source_graph.ModelManager,
            "get_defaults",
            new=AsyncMock(
                return_value=SimpleNamespace(default_speech_to_text_model=None)
            ),
        ),
        patch.object(source_graph, "extract_content", new=extract),
    ):
        return await source_graph.content_process({"content_state": state})  # type: ignore[typeddict-item]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state,error,expected",
    [
        ({"url": YOUTUBE}, cc.NoTranscriptFound("none"), "Speech-to-Text model"),
        ({"url": YOUTUBE}, cc.ExternalServiceError("IpBlocked"), "CCORE_YOUTUBE_PROXY"),
        ({"url": PAGE}, cc.NotFoundError("HTTP 404"), "page was not found"),
        ({"url": PAGE}, cc.NetworkError("DNS failure"), "Could not reach"),
        ({"url": "nota url"}, cc.InvalidInputError("malformed"), "not valid"),
        (
            {"file_path": "/tmp/x.bin"},
            cc.UnsupportedTypeException("application/x-foo"),
            "not supported",
        ),
        (
            {"file_path": "/tmp/x.pdf"},
            cc.FileOperationError("corrupted PDF"),
            "could not be read",
        ),
        (
            {"url": PAGE},
            cc.ConfigurationError("crawl4ai not installed"),
            "not configured correctly",
        ),
        ({"url": PAGE}, cc.ExternalServiceError("firecrawl 500"), "service failed"),
        ({"url": PAGE}, cc.ContentCoreError("odd"), "Could not extract content"),
    ],
)
async def test_typed_errors_become_permanent_user_facing_failures(
    state, error, expected
):
    with pytest.raises(ValueError, match=expected) as excinfo:
        await _run(state, AsyncMock(side_effect=error))

    # The original error stays attached for the worker log.
    assert excinfo.value.__cause__ is error


@pytest.mark.asyncio
async def test_raw_detail_stays_out_of_the_user_message():
    """content-core's text can carry proxy credentials or local paths; it goes
    to the log and the exception chain, not the client-visible message."""
    secret = "proxy http://user:hunter2@10.0.0.5:3128 failed for /app/data/x.pdf"
    with pytest.raises(ValueError) as excinfo:
        await _run({"url": PAGE}, AsyncMock(side_effect=cc.NetworkError(secret)))

    message = str(excinfo.value)
    assert "hunter2" not in message
    assert "/app/data" not in message
    assert str(excinfo.value.__cause__) == secret


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/watch?v=abc", True),
        ("https://youtube.com/shorts/abc", True),
        ("https://m.youtube.com/watch?v=abc", True),
        ("https://youtu.be/abc", True),
        ("https://notyoutube.com/watch?v=abc", False),
        ("https://example.com/youtube.com/abc", False),
        ("", False),
    ],
)
def test_is_youtube_url_matches_hostnames(url, expected):
    assert source_graph._is_youtube_url(url) is expected


@pytest.mark.asyncio
async def test_blocked_non_youtube_url_gets_generic_service_message():
    with pytest.raises(ValueError, match="service failed") as excinfo:
        await _run(
            {"url": "https://notyoutube.com/watch?v=abc"},
            AsyncMock(side_effect=cc.ExternalServiceError("blocked")),
        )
    assert "CCORE_YOUTUBE_PROXY" not in str(excinfo.value)


@pytest.mark.asyncio
async def test_genuinely_empty_youtube_content_keeps_the_stt_hint():
    empty = SimpleNamespace(title="Video", content="")
    with pytest.raises(ValueError, match="Speech-to-Text model"):
        await _run({"url": YOUTUBE}, AsyncMock(return_value=empty))


def test_value_error_is_permanent_for_process_source():
    """The mapping relies on ValueError being in process_source's stop_on."""
    from surreal_commands import registry

    import commands.source_commands  # noqa: F401  (registers the command)

    command = registry.get_command("open_notebook", "process_source")
    assert command is not None
    assert ValueError in command.retry_config.stop_on
