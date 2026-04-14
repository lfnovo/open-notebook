"""
Tests for Workspace API routes and RBAC middleware.

Tests cover CRUD endpoints, role enforcement, member management,
and workspace discovery — all using mocked domain models.
No running database or API server required.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jwcrypto import jwk

from api.clerk_auth import ClerkAuthMiddleware, clear_jwks_cache


# =============================================================================
# TEST FIXTURES — RSA key pair, JWT factory, test app
# =============================================================================


def _generate_rsa_key_pair():
    """Generate an RSA private key and matching JWK for JWKS mock."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    jwk_key = jwk.JWK.from_pem(public_pem)
    jwk_dict = jwk_key.export(as_dict=True)
    jwk_dict["kid"] = "test-key-1"
    jwk_dict["use"] = "sig"
    jwk_dict["alg"] = "RS256"
    return private_key, jwk_dict


PRIVATE_KEY, JWK_DICT = _generate_rsa_key_pair()
JWKS_RESPONSE = {"keys": [JWK_DICT]}

TEST_ISSUER = "https://test-app.clerk.accounts.dev"
TEST_JWKS_URL = "https://test-app.clerk.accounts.dev/.well-known/jwks.json"


def _make_jwt(sub="user_owner", org_id="org_1"):
    """Build a signed JWT for testing."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": TEST_ISSUER,
        "iat": now,
        "exp": now + 3600,
        "nbf": now - 10,
    }
    if org_id is not None:
        payload["org_id"] = org_id
    return jwt.encode(
        payload, PRIVATE_KEY, algorithm="RS256", headers={"kid": "test-key-1"}
    )


def _auth_headers(sub="user_owner", org_id="org_1"):
    """Return Authorization headers for the given user."""
    token = _make_jwt(sub=sub, org_id=org_id)
    return {"Authorization": f"Bearer {token}"}


def _build_test_app():
    """Build a FastAPI app with ClerkAuth + workspace router for testing."""
    from api.routers.workspaces import router as workspace_router

    app = FastAPI()
    app.add_middleware(
        ClerkAuthMiddleware,
        jwks_url=TEST_JWKS_URL,
        issuer=TEST_ISSUER,
        excluded_paths=["/health"],
    )
    app.include_router(workspace_router, prefix="/api")
    return app


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    clear_jwks_cache()
    yield
    clear_jwks_cache()


@pytest.fixture
def mock_jwks():
    async def fake_fetch_jwks(jwks_url: str) -> dict:
        return JWKS_RESPONSE

    with patch("api.clerk_auth._fetch_jwks", fake_fetch_jwks):
        yield


@pytest.fixture
def test_app():
    return _build_test_app()


def _workspace_dict(
    workspace_id="workspace:ws1",
    name="Test KB",
    visibility="private",
    owner_id="user_owner",
    org_id="org_1",
):
    """Factory for workspace data returned from mocked domain methods."""
    return {
        "id": workspace_id,
        "name": name,
        "description": None,
        "visibility": visibility,
        "owner_id": owner_id,
        "org_id": org_id,
        "created": "2026-04-12T00:00:00",
        "updated": "2026-04-12T00:00:00",
    }


def _member_dict(
    member_id="workspace_member:m1",
    workspace_id="workspace:ws1",
    user_id="user_owner",
    role="owner",
):
    """Factory for workspace member data returned from mocked domain methods."""
    return {
        "id": member_id,
        "workspace_id": workspace_id,
        "user_id": user_id,
        "role": role,
        "created": "2026-04-12T00:00:00",
        "updated": "2026-04-12T00:00:00",
    }


def _make_workspace(
    workspace_id="workspace:ws1",
    name="Test KB",
    visibility="private",
    owner_id="user_owner",
    org_id="org_1",
):
    from open_notebook.domain.workspace import Workspace

    return Workspace(
        **_workspace_dict(workspace_id, name, visibility, owner_id, org_id)
    )


def _make_member(
    member_id="workspace_member:m1",
    workspace_id="workspace:ws1",
    user_id="user_owner",
    role="owner",
):
    from open_notebook.domain.workspace import WorkspaceMember

    return WorkspaceMember(**_member_dict(member_id, workspace_id, user_id, role))


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================


class TestCreateWorkspace:
    """POST /api/workspaces — create workspace, auto-add creator as Owner."""

    @pytest.mark.asyncio
    async def test_create_workspace_auto_owner(self, test_app, mock_jwks):
        """POST /api/workspaces -> user becomes Owner. 201 returned."""
        workspace = _make_workspace()
        member = _make_member()

        with (
            patch("api.workspace_service.Workspace") as MockWorkspace,
            patch("api.workspace_service.WorkspaceMember") as MockMember,
        ):
            mock_ws_instance = AsyncMock()
            mock_ws_instance.id = "workspace:ws1"
            mock_ws_instance.name = "KB"
            mock_ws_instance.description = None
            mock_ws_instance.visibility = "private"
            mock_ws_instance.owner_id = "user_owner"
            mock_ws_instance.org_id = "org_1"
            mock_ws_instance.created = "2026-04-12T00:00:00"
            mock_ws_instance.updated = "2026-04-12T00:00:00"
            MockWorkspace.return_value = mock_ws_instance

            mock_member_instance = AsyncMock()
            mock_member_instance.id = "workspace_member:m1"
            mock_member_instance.role = "owner"
            MockMember.return_value = mock_member_instance

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces",
                    json={"name": "KB", "visibility": "private"},
                    headers=_auth_headers(),
                )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "KB"
        assert body["owner_id"] == "user_owner"


class TestListWorkspaces:
    """GET /api/workspaces — list workspaces for authenticated user."""

    @pytest.mark.asyncio
    async def test_list_workspaces_only_accessible(self, test_app, mock_jwks):
        """User with 2 memberships, 3 total workspaces -> sees only 2."""
        memberships = [
            _make_member(
                member_id="workspace_member:m1",
                workspace_id="workspace:ws1",
                user_id="user_owner",
                role="owner",
            ),
            _make_member(
                member_id="workspace_member:m2",
                workspace_id="workspace:ws2",
                user_id="user_owner",
                role="editor",
            ),
        ]
        workspaces = [
            _make_workspace(workspace_id="workspace:ws1", name="WS1"),
            _make_workspace(workspace_id="workspace:ws2", name="WS2"),
        ]

        with (
            patch(
                "api.workspace_service.WorkspaceMember.get_for_user",
                new_callable=AsyncMock,
                return_value=memberships,
            ),
            patch(
                "api.workspace_service.Workspace.get",
                new_callable=AsyncMock,
                side_effect=workspaces,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/workspaces",
                    headers=_auth_headers(),
                )

        assert response.status_code == 200
        assert len(response.json()) == 2


class TestDiscoverWorkspaces:
    """GET /api/workspaces/discover — discover community workspaces."""

    @pytest.mark.asyncio
    async def test_discover_community_workspaces(self, test_app, mock_jwks):
        """Community workspace in same org -> appears in discover."""
        community_ws = _make_workspace(
            workspace_id="workspace:community1",
            name="Community KB",
            visibility="community",
            owner_id="user_other",
            org_id="org_1",
        )

        with patch(
            "api.workspace_service.repo_query",
            new_callable=AsyncMock,
            return_value=[
                _workspace_dict(
                    workspace_id="workspace:community1",
                    name="Community KB",
                    visibility="community",
                    owner_id="user_other",
                    org_id="org_1",
                )
            ],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/workspaces/discover",
                    headers=_auth_headers(sub="user_owner", org_id="org_1"),
                )

        assert response.status_code == 200
        body = response.json()
        assert len(body) >= 1
        assert body[0]["name"] == "Community KB"


class TestInviteMember:
    """POST /api/workspaces/{id}/members — invite a member."""

    @pytest.mark.asyncio
    async def test_invite_member(self, test_app, mock_jwks):
        """Owner invites user as viewer -> membership created. 201."""
        owner_member = _make_member(
            user_id="user_owner", workspace_id="workspace:ws1", role="owner"
        )
        new_member = _make_member(
            member_id="workspace_member:m2",
            workspace_id="workspace:ws1",
            user_id="user_new",
            role="viewer",
        )

        with (
            patch(
                "api.rbac.repo_query",
                new_callable=AsyncMock,
                return_value=[{"role": "owner"}],
            ),
            patch(
                "api.routers.workspaces.invite_member",
                new_callable=AsyncMock,
                return_value=new_member,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces/workspace:ws1/members",
                    json={"user_id": "user_new", "role": "viewer"},
                    headers=_auth_headers(sub="user_owner"),
                )

        assert response.status_code == 201


class TestEditorCannotDelete:
    """Editor role enforcement on DELETE workspace."""

    @pytest.mark.asyncio
    async def test_editor_cannot_delete_workspace(self, test_app, mock_jwks):
        """Editor calls DELETE -> 403."""
        editor_member = _make_member(
            user_id="user_editor", workspace_id="workspace:ws1", role="editor"
        )

        with patch(
            "api.rbac.repo_query",
            new_callable=AsyncMock,
            return_value=[{"role": "editor"}],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    "/api/workspaces/workspace:ws1?confirm=true",
                    headers=_auth_headers(sub="user_editor"),
                )

        assert response.status_code == 403


# =============================================================================
# ERROR CASES
# =============================================================================


class TestNonMemberAccess:
    """Non-member access denied on workspace-scoped endpoints."""

    @pytest.mark.asyncio
    async def test_non_member_gets_403(self, test_app, mock_jwks):
        """Non-member calls GET workspace -> 403."""
        with patch(
            "api.rbac.repo_query",
            new_callable=AsyncMock,
            return_value=[],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/workspaces/workspace:ws1",
                    headers=_auth_headers(sub="user_stranger"),
                )

        assert response.status_code == 403


class TestViewerCannotModify:
    """Viewer role enforcement on write endpoints."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_modify(self, test_app, mock_jwks):
        """Viewer calls PUT workspace -> 403."""
        viewer_member = _make_member(
            user_id="user_viewer", workspace_id="workspace:ws1", role="viewer"
        )

        with patch(
            "api.rbac.repo_query",
            new_callable=AsyncMock,
            return_value=[{"role": "viewer"}],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/workspaces/workspace:ws1",
                    json={"name": "Hacked"},
                    headers=_auth_headers(sub="user_viewer"),
                )

        assert response.status_code == 403


class TestDeleteWithoutConfirmation:
    """DELETE workspace requires confirmation flag."""

    @pytest.mark.asyncio
    async def test_delete_without_confirmation_fails(self, test_app, mock_jwks):
        """DELETE without confirm flag -> 400."""
        owner_member = _make_member(
            user_id="user_owner", workspace_id="workspace:ws1", role="owner"
        )

        with patch(
            "api.rbac.repo_query",
            new_callable=AsyncMock,
            return_value=[{"role": "owner"}],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    "/api/workspaces/workspace:ws1",
                    headers=_auth_headers(sub="user_owner"),
                )

        assert response.status_code == 400


# =============================================================================
# ADVERSARIAL CASES
# =============================================================================


class TestRBACBypassViaDirectId:
    """Non-member crafting a workspace_id should get 403, not 404."""

    @pytest.mark.asyncio
    async def test_rbac_bypass_via_direct_id(self, test_app, mock_jwks):
        """Non-member crafts workspace_id -> 403 (not 404)."""
        with patch(
            "api.rbac.repo_query",
            new_callable=AsyncMock,
            return_value=[],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/workspaces/workspace:unknown_id",
                    headers=_auth_headers(sub="user_attacker"),
                )

        assert response.status_code == 403


class TestInviteSelfAsOwner:
    """Editor cannot promote themselves to owner via invite."""

    @pytest.mark.asyncio
    async def test_invite_self_as_owner(self, test_app, mock_jwks):
        """Editor tries to invite themselves as Owner -> 403."""
        editor_member = _make_member(
            user_id="user_editor", workspace_id="workspace:ws1", role="editor"
        )

        with patch(
            "api.rbac.repo_query",
            new_callable=AsyncMock,
            return_value=[{"role": "editor"}],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces/workspace:ws1/members",
                    json={"user_id": "user_editor", "role": "owner"},
                    headers=_auth_headers(sub="user_editor"),
                )

        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
