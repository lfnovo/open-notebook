from unittest.mock import AsyncMock, patch

import pytest

from api.services.source_service import retry_source_processing_use_case
from open_notebook.domain.notebook import Asset, Source


@pytest.mark.asyncio
async def test_retry_marks_submitted_command_failed_when_source_update_fails():
    source = Source(
        id="source:retry",
        title="Retry me",
        asset=Asset(url="https://example.com/article"),
        owner_id="user:owner",
        visibility="private",
    )

    async def fail_save(self):
        raise RuntimeError("database update failed")

    with patch.object(Source, "get", new_callable=AsyncMock, return_value=source):
        with patch.object(Source, "save", autospec=True, side_effect=fail_save):
            with patch(
                "api.services.source_service.SourceRepository.referenced_notebook_ids",
                new_callable=AsyncMock,
                return_value=["notebook:one"],
            ):
                with patch(
                    "api.services.source_service.submit_process_source_command",
                    new_callable=AsyncMock,
                    return_value="command:retry",
                ):
                    with patch(
                        "api.services.source_service.resolve_resource_team_context",
                        new_callable=AsyncMock,
                        return_value=None,
                    ):
                        with patch(
                            "api.services.source_service.mark_command_failed",
                            new_callable=AsyncMock,
                        ) as mark_failed:
                            with pytest.raises(
                                RuntimeError, match="database update failed"
                            ):
                                await retry_source_processing_use_case(
                                    "source:retry",
                                    user_id="user:owner",
                                )

    mark_failed.assert_awaited_once()
    args = mark_failed.await_args.args
    assert args[0] == "command:retry"
    assert "Failed to attach command to source source:retry" in args[1]
