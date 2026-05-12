from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import (
    ExternalApiConnectionCreate,
    ExternalApiSearchRequest,
    ExternalSourceCreate,
)
from api.services import external_api_service
from commands.external_api_commands import ExternalSearchInput, external_source_search_command
from open_notebook.exceptions import InvalidInputError


def admin_actor() -> CurrentUser:
    return CurrentUser(id="app_user:admin", username="admin", role="admin")


def team_member_actor() -> CurrentUser:
    return CurrentUser(id="app_user:member", username="member", role="user")


@pytest.mark.asyncio
@patch("api.services.external_api_service.ExternalApiRepository.create_connection", new_callable=AsyncMock)
@patch("api.services.external_api_service.encrypt_value")
async def test_create_connection_encrypts_api_key_and_masks_response(
    mock_encrypt,
    mock_create_connection,
):
    mock_encrypt.return_value = "encrypted-secret"
    mock_create_connection.return_value = {
        "id": "external_api_connection:paper",
        "name": "Paper Search",
        "base_url": "https://papers.example.com",
        "api_key": "encrypted-secret",
        "manifest": {"name": "Paper Search"},
        "enabled": True,
        "timeout_seconds": 30,
        "created_by": "app_user:admin",
        "created": "2026-05-11T00:00:00Z",
        "updated": "2026-05-11T00:00:00Z",
    }

    response = await external_api_service.create_connection_use_case(
        ExternalApiConnectionCreate(
            name="Paper Search",
            base_url="https://papers.example.com/",
            api_key="plain-secret",
            timeout_seconds=30,
        ),
        actor=admin_actor(),
    )

    mock_encrypt.assert_called_once_with("plain-secret")
    mock_create_connection.assert_awaited_once()
    stored_payload = mock_create_connection.await_args.args[0]
    assert stored_payload["api_key"] == "encrypted-secret"
    assert response.id == "external_api_connection:paper"
    assert response.api_key_configured is True
    assert not hasattr(response, "api_key")
    assert response.target_type == "source"


@pytest.mark.asyncio
@patch("api.services.external_api_service.ExternalApiRepository.create_connection", new_callable=AsyncMock)
@patch("api.services.external_api_service.encrypt_value")
async def test_create_connection_stores_output_target_type(
    mock_encrypt,
    mock_create_connection,
):
    mock_encrypt.return_value = "encrypted-secret"
    mock_create_connection.return_value = {
        "id": "external_api_connection:output",
        "name": "Output Writer",
        "target_type": "output",
        "base_url": "https://outputs.example.com",
        "api_key": "encrypted-secret",
        "manifest": None,
        "enabled": True,
        "timeout_seconds": 30,
        "created_by": "app_user:admin",
        "created": "2026-05-11T00:00:00Z",
        "updated": "2026-05-11T00:00:00Z",
    }

    response = await external_api_service.create_connection_use_case(
        ExternalApiConnectionCreate(
            name="Output Writer",
            target_type="output",
            base_url="https://outputs.example.com/",
            api_key="plain-secret",
        ),
        actor=admin_actor(),
    )

    stored_payload = mock_create_connection.await_args.args[0]
    assert stored_payload["target_type"] == "output"
    assert response.target_type == "output"


@pytest.mark.asyncio
@patch("api.services.external_api_service.ExternalApiRepository.get_connection", new_callable=AsyncMock)
async def test_create_source_rejects_output_connection(mock_get_connection):
    mock_get_connection.return_value = {
        "id": "external_api_connection:output",
        "name": "Output Writer",
        "target_type": "output",
        "enabled": True,
    }

    with pytest.raises(InvalidInputError):
        await external_api_service.create_source_use_case(
            ExternalSourceCreate(
                connection_id="external_api_connection:output",
                name="Output Writer",
                key="output_writer",
                capabilities=["output"],
            ),
            actor=admin_actor(),
        )


@pytest.mark.asyncio
@patch("api.services.external_api_service.CommandService.submit_command_job", new_callable=AsyncMock)
@patch("api.services.external_api_service.ExternalApiRepository.month_usage_count", new_callable=AsyncMock)
@patch("api.services.external_api_service.ExternalApiRepository.get_active_team_grant", new_callable=AsyncMock)
@patch("api.services.external_api_service.TeamRepository.get_member", new_callable=AsyncMock)
async def test_submit_search_requires_grant_but_does_not_consume_quota(
    mock_get_member,
    mock_get_grant,
    mock_usage_count,
    mock_submit_command,
):
    mock_get_member.return_value = {"role": "member", "status": "active"}
    mock_get_grant.return_value = {
        "id": "external_source_team_grant:grant",
        "team": "team:research",
        "source": "external_source:papers",
        "monthly_request_quota": 2,
        "enabled": True,
    }
    mock_usage_count.return_value = 2
    mock_submit_command.return_value = "command:search"

    response = await external_api_service.submit_search_use_case(
        "external_source:papers",
        ExternalApiSearchRequest(
            team_id="team:research",
            query="graph retrieval",
            limit=10,
        ),
        actor=team_member_actor(),
    )

    assert response.command_id == "command:search"
    mock_get_grant.assert_awaited_once()
    mock_usage_count.assert_not_awaited()
    mock_submit_command.assert_awaited_once()


@pytest.mark.asyncio
@patch("commands.external_api_commands.ExternalApiRepository.update_usage_status", new_callable=AsyncMock)
@patch("commands.external_api_commands.ExternalApiRepository.create_usage", new_callable=AsyncMock)
@patch("commands.external_api_commands.ExternalApiRepository.upsert_item", new_callable=AsyncMock)
@patch("commands.external_api_commands._client_for_source", new_callable=AsyncMock)
@patch("commands.external_api_commands.ExternalApiRepository.get_source", new_callable=AsyncMock)
async def test_external_search_command_does_not_record_usage(
    mock_get_source,
    mock_client_for_source,
    mock_upsert_item,
    mock_create_usage,
    mock_update_usage,
):
    mock_get_source.return_value = {
        "id": "external_source:papers",
        "key": "paper_search",
        "enabled": True,
    }
    mock_client = AsyncMock()
    mock_client.search_sources.return_value = {
        "status": "completed",
        "data": {
            "items": [
                {
                    "external_id": "paper:one",
                    "title": "Paper One",
                    "summary": "A paper.",
                }
            ]
        },
    }
    mock_client.wait_for_result.return_value = mock_client.search_sources.return_value
    mock_client_for_source.return_value = mock_client
    mock_upsert_item.return_value = {
        "id": "external_source_item:paper_one",
        "title": "Paper One",
    }

    result = await external_source_search_command(
        ExternalSearchInput(
            actor_id="app_user:member",
            team_id="team:research",
            source_id="external_source:papers",
            grant_id="external_source_team_grant:grant",
            query="paper",
            limit=10,
        )
    )

    assert result.success is True
    assert result.item_count == 1
    mock_create_usage.assert_not_awaited()
    mock_update_usage.assert_not_awaited()
