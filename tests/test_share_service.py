from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.services.share_service import delete_share_grant_use_case


@pytest.mark.asyncio
@patch("api.services.share_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.share_service.repo_update", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.delete_grant", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.create_grant", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.referencing_notebook_owner_ids", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.get_grant", new_callable=AsyncMock)
@patch("api.services.share_service._resource_owner", new_callable=AsyncMock)
async def test_public_revoke_preserves_existing_reference_owners(
    mock_owner,
    mock_get_grant,
    mock_reference_owners,
    mock_create_grant,
    mock_delete_grant,
    mock_repo_update,
    mock_audit,
    monkeypatch,
):
    monkeypatch.setenv("PUBLIC_SHARE_REVOCATION_MODE", "preserve_references")
    mock_owner.return_value = "app_user:owner"
    mock_get_grant.return_value = {
        "id": "share_grant:public",
        "resource_type": "source",
        "resource_id": "source:abc",
        "target_type": "team",
        "target_id": "team:public",
    }
    mock_reference_owners.return_value = ["app_user:reader"]
    mock_create_grant.return_value = {"id": "share_grant:reader"}

    actor = CurrentUser(id="app_user:owner", username="owner", role="user")

    response = await delete_share_grant_use_case("share_grant:public", actor=actor)

    assert response.success is True
    mock_create_grant.assert_awaited_once_with(
        resource_type="source",
        resource_id="source:abc",
        target_type="user",
        target_id="app_user:reader",
        permission="read",
        created_by="app_user:owner",
    )
    mock_repo_update.assert_awaited_once_with(
        "source", "source:abc", {"visibility": "private"}
    )
    mock_audit.assert_awaited_once()
    assert mock_audit.await_args.kwargs["metadata"]["preserved_grants_count"] == 1


@pytest.mark.asyncio
@patch("api.services.share_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.share_service.repo_update", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.delete_grant", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.notebook_source_ids", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.list_resource_grants", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.create_grant", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.referencing_notebook_owner_ids", new_callable=AsyncMock)
@patch("api.services.share_service.ShareRepository.get_grant", new_callable=AsyncMock)
@patch("api.services.share_service._resource_owner", new_callable=AsyncMock)
async def test_public_notebook_revoke_preserves_source_access_for_existing_grants(
    mock_owner,
    mock_get_grant,
    mock_reference_owners,
    mock_create_grant,
    mock_list_grants,
    mock_source_ids,
    mock_delete_grant,
    mock_repo_update,
    mock_audit,
    monkeypatch,
):
    monkeypatch.setenv("PUBLIC_SHARE_REVOCATION_MODE", "preserve_references")
    mock_owner.return_value = "app_user:owner"
    mock_get_grant.return_value = {
        "id": "share_grant:public",
        "resource_type": "notebook",
        "resource_id": "notebook:abc",
        "target_type": "team",
        "target_id": "team:public",
    }
    mock_reference_owners.return_value = []
    mock_list_grants.return_value = [
        {
            "id": "share_grant:team",
            "resource_type": "notebook",
            "resource_id": "notebook:abc",
            "target_type": "team",
            "target_id": "team:research",
        },
        {
            "id": "share_grant:public",
            "resource_type": "notebook",
            "resource_id": "notebook:abc",
            "target_type": "team",
            "target_id": "team:public",
        },
    ]
    mock_source_ids.return_value = ["source:one", "source:two"]
    mock_create_grant.return_value = {"id": "share_grant:preserved"}

    actor = CurrentUser(id="app_user:owner", username="owner", role="user")

    response = await delete_share_grant_use_case("share_grant:public", actor=actor)

    assert response.success is True
    assert mock_create_grant.await_count == 2
    mock_create_grant.assert_any_await(
        resource_type="source",
        resource_id="source:one",
        target_type="team",
        target_id="team:research",
        permission="read",
        created_by="app_user:owner",
    )
    mock_create_grant.assert_any_await(
        resource_type="source",
        resource_id="source:two",
        target_type="team",
        target_id="team:research",
        permission="read",
        created_by="app_user:owner",
    )
    mock_repo_update.assert_awaited_once_with(
        "notebook", "notebook:abc", {"visibility": "private"}
    )
    assert mock_audit.await_args.kwargs["metadata"]["preserved_grants_count"] == 2
