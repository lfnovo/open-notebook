"""A source that fails processing must not stay titled "Processing..." (#1397)."""

from unittest.mock import AsyncMock, patch

import pytest

import commands  # noqa: F401 -- import registers the @command decorators
from open_notebook.domain.notebook import (
    PLACEHOLDER_SOURCE_TITLE,
    fallback_source_title,
    is_replaceable_source_title,
)


def test_fallback_title_prefers_url_then_file_name():
    assert fallback_source_title(url="https://example.com/a") == "https://example.com/a"
    assert fallback_source_title(file_path="/data/uploads/report.pdf") == "report.pdf"
    assert fallback_source_title() is None
    assert fallback_source_title(url="  ") is None


def test_replaceable_titles():
    url = "https://example.com/a"
    assert is_replaceable_source_title(None)
    assert is_replaceable_source_title(PLACEHOLDER_SOURCE_TITLE)
    # the fallback written by a failed attempt gives way to the real title
    assert is_replaceable_source_title(url, url=url)
    assert is_replaceable_source_title("report.pdf", file_path="/x/report.pdf")
    assert not is_replaceable_source_title("My own title", url=url)


async def _fail_processing(content_state, error):
    from commands.source_commands import SourceProcessingInput, process_source_command

    input_data = SourceProcessingInput(
        source_id="source:abc",
        content_state=content_state,
        notebook_ids=[],
        transformations=[],
        embed=False,
    )
    repo_query = AsyncMock(return_value=[])
    with (
        patch("commands.source_commands.Source.get", new=AsyncMock(side_effect=error)),
        patch("commands.source_commands.repo_query", new=repo_query),
    ):
        with pytest.raises(type(error)):
            await process_source_command(input_data)
    return repo_query


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [ValueError("bad input"), RuntimeError("boom")])
async def test_failure_replaces_placeholder_with_url(error):
    repo_query = await _fail_processing({"url": "https://example.com/a"}, error)

    query, params = repo_query.await_args.args
    assert "SET title = $title WHERE title = $placeholder" in query
    assert params["title"] == "https://example.com/a"
    assert params["placeholder"] == PLACEHOLDER_SOURCE_TITLE


@pytest.mark.asyncio
async def test_failure_clears_placeholder_when_there_is_no_url_or_file():
    repo_query = await _fail_processing({"content": "pasted"}, ValueError("bad"))

    query, _ = repo_query.await_args.args
    assert "SET title = NONE WHERE title = $placeholder" in query


@pytest.mark.asyncio
async def test_title_update_failure_does_not_mask_the_original_error():
    from commands.source_commands import SourceProcessingInput, process_source_command

    input_data = SourceProcessingInput(
        source_id="source:abc",
        content_state={"url": "https://example.com/a"},
        notebook_ids=[],
        transformations=[],
        embed=False,
    )
    with (
        patch(
            "commands.source_commands.Source.get",
            new=AsyncMock(side_effect=ValueError("original")),
        ),
        patch(
            "commands.source_commands.repo_query",
            new=AsyncMock(side_effect=RuntimeError("db down")),
        ),
    ):
        with pytest.raises(ValueError, match="original"):
            await process_source_command(input_data)


def test_processing_info_error_is_capped():
    from api.routers.sources import _with_truncated_error

    info = _with_truncated_error({"status": "failed", "error": "x" * 500})
    assert info is not None and len(info["error"]) == 201
    assert _with_truncated_error(None) is None
    assert _with_truncated_error({"status": "running", "error": None}) == {
        "status": "running",
        "error": None,
    }
