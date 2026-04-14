"""
Tests for Phase 4 — Source Ingestion (Workspace-Scoped + RAGAnything).

Covers workspace-scoped upload, file size validation, duplicate detection,
RAGAnything extraction with fallback, and RBAC enforcement.

All tests mock DB and service operations — no running database required.
"""

import time
from io import BytesIO
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
# FIXTURES — RSA key pair, JWT factory, test app
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


def _make_jwt(sub="user_editor", org_id="org_1"):
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


def _auth_headers(sub="user_editor", org_id="org_1"):
    """Return Authorization headers for the given user."""
    token = _make_jwt(sub=sub, org_id=org_id)
    return {"Authorization": f"Bearer {token}"}


def _build_test_app():
    """Build a FastAPI app with ClerkAuth + sources router for testing."""
    from api.routers.sources import router as sources_router

    app = FastAPI()
    app.add_middleware(
        ClerkAuthMiddleware,
        jwks_url=TEST_JWKS_URL,
        issuer=TEST_ISSUER,
        excluded_paths=["/health"],
    )
    app.include_router(sources_router, prefix="/api")
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


# =============================================================================
# FACTORIES
# =============================================================================


def _make_member(
    member_id="workspace_member:m1",
    workspace_id="workspace:ws1",
    user_id="user_editor",
    role="editor",
):
    from open_notebook.domain.workspace import WorkspaceMember

    return WorkspaceMember(
        id=member_id,
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
        created="2026-04-12T00:00:00",
        updated="2026-04-12T00:00:00",
    )


def _make_source(
    source_id="source:src1",
    title="Test Source",
    workspace_id="workspace:ws1",
):
    from open_notebook.domain.notebook import Source

    source = Source(
        title=title,
        topics=[],
        workspace_id=workspace_id,
    )
    source.id = source_id
    source.created = "2026-04-12T00:00:00"
    source.updated = "2026-04-12T00:00:00"
    return source


def _small_file_bytes(size_bytes=1024, filename="test.txt"):
    """Create a small in-memory file for upload."""
    return ("file", (filename, BytesIO(b"x" * size_bytes), "text/plain"))


def _large_file_bytes(size_mb=51, filename="huge.pdf"):
    """Create a file exceeding the 50MB limit."""
    size_bytes = size_mb * 1024 * 1024
    # Use a generator-backed BytesIO to avoid allocating 51MB in RAM
    content = b"x" * (1024 * 1024)  # 1MB chunk
    buf = BytesIO()
    for _ in range(size_mb):
        buf.write(content)
    remaining = size_bytes - (size_mb * 1024 * 1024)
    if remaining > 0:
        buf.write(b"x" * remaining)
    buf.seek(0)
    return ("file", (filename, buf, "application/pdf"))


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================


class TestUploadSourceToWorkspace:
    """POST /api/workspaces/{workspace_id}/sources — workspace-scoped upload."""

    @pytest.mark.asyncio
    async def test_upload_source_to_workspace(self, test_app, mock_jwks):
        """Upload file to workspace -> source created with workspace_id. 202."""
        editor_member = _make_member(role="editor")
        source = _make_source()

        with (
            patch(
                "api.rbac.repo_query",
                new_callable=AsyncMock,
                return_value=[{"role": "editor"}],
            ),
            patch(
                "api.routers.sources.save_uploaded_file",
                new_callable=AsyncMock,
                return_value="/uploads/test.txt",
            ),
            patch(
                "api.routers.sources.Source",
            ) as MockSource,
            patch(
                "api.routers.sources.CommandService",
            ) as MockCommandService,
            patch(
                "api.routers.sources.ensure_record_id",
                side_effect=lambda x: x,
            ),
            patch(
                "api.routers.sources.repo_query",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            mock_source_instance = AsyncMock()
            mock_source_instance.id = "source:src1"
            mock_source_instance.title = "Processing..."
            mock_source_instance.topics = []
            mock_source_instance.asset = None
            mock_source_instance.workspace_id = "workspace:ws1"
            mock_source_instance.created = "2026-04-12T00:00:00"
            mock_source_instance.updated = "2026-04-12T00:00:00"
            mock_source_instance.command = None
            MockSource.return_value = mock_source_instance

            MockCommandService.submit_command_job = AsyncMock(
                return_value="command:cmd1"
            )

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces/workspace:ws1/sources",
                    data={"type": "upload", "async_processing": "true"},
                    files=[_small_file_bytes()],
                    headers=_auth_headers(sub="user_editor"),
                )

        assert response.status_code == 202
        body = response.json()
        assert body["workspace_id"] == "workspace:ws1"

    @pytest.mark.asyncio
    async def test_source_has_workspace_id(self, test_app, mock_jwks):
        """Uploaded source -> workspace_id set correctly in Source constructor."""
        editor_member = _make_member(role="editor")

        captured_kwargs = {}

        def capture_source(**kwargs):
            captured_kwargs.update(kwargs)
            mock_instance = AsyncMock()
            mock_instance.id = "source:src2"
            mock_instance.title = kwargs.get("title", "Processing...")
            mock_instance.topics = kwargs.get("topics", [])
            mock_instance.asset = None
            mock_instance.workspace_id = kwargs.get("workspace_id")
            mock_instance.created = "2026-04-12T00:00:00"
            mock_instance.updated = "2026-04-12T00:00:00"
            mock_instance.command = None
            return mock_instance

        with (
            patch(
                "api.rbac.repo_query",
                new_callable=AsyncMock,
                return_value=[{"role": "editor"}],
            ),
            patch(
                "api.routers.sources.Source",
                side_effect=capture_source,
            ),
            patch(
                "api.routers.sources.CommandService",
            ) as MockCommandService,
            patch(
                "api.routers.sources.ensure_record_id",
                side_effect=lambda x: x,
            ),
            patch(
                "api.routers.sources.repo_query",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            MockCommandService.submit_command_job = AsyncMock(
                return_value="command:cmd1"
            )

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces/workspace:ws1/sources",
                    data={
                        "type": "text",
                        "content": "Hello world",
                        "async_processing": "true",
                    },
                    headers=_auth_headers(sub="user_editor"),
                )

        assert response.status_code == 202
        assert captured_kwargs.get("workspace_id") == "workspace:ws1"


class TestDeleteSourceRemovesEmbeddings:
    """DELETE /api/sources/{id} -> embeddings cleaned up."""

    @pytest.mark.asyncio
    async def test_delete_source_removes_embeddings(self, test_app, mock_jwks):
        """Delete source -> embeddings and insights cleaned up via Source.delete."""
        mock_source = AsyncMock()
        mock_source.id = "source:src1"
        mock_source.workspace_id = None  # Legacy source, no workspace RBAC
        mock_source.delete = AsyncMock(return_value=True)

        with patch(
            "api.routers.sources.Source.get",
            new_callable=AsyncMock,
            return_value=mock_source,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    "/api/sources/source:src1",
                    headers=_auth_headers(),
                )

        assert response.status_code == 200
        mock_source.delete.assert_awaited_once()


class TestRagAnythingExtraction:
    """RAGAnything extraction for PDF files."""

    @pytest.mark.asyncio
    async def test_raganything_extraction_for_pdf(self):
        """PDF processed via RAGAnything (mocked). Expected: extracted text returned."""
        from open_notebook.services.ingestion_service import raganything_extract

        mock_rag = MagicMock()
        mock_rag.process_document = AsyncMock(
            return_value={"content": "Extracted PDF text with tables"}
        )

        with patch(
            "open_notebook.services.ingestion_service._try_import_raganything",
            return_value=mock_rag,
        ):
            result = await raganything_extract("/path/to/doc.pdf")

        assert result is not None
        assert "Extracted PDF text" in result

    @pytest.mark.asyncio
    async def test_contentcore_fallback_for_txt(self):
        """TXT file uses content-core. Expected: raganything_extract returns None."""
        from open_notebook.services.ingestion_service import raganything_extract

        result = await raganything_extract("/path/to/file.txt")
        assert result is None


# =============================================================================
# ERROR CASES
# =============================================================================


class TestUploadExceeds50MB:
    """File size > 50MB rejected before upload."""

    @pytest.mark.asyncio
    async def test_upload_exceeds_50mb(self, test_app, mock_jwks):
        """51MB file -> rejected with 413 size error."""
        editor_member = _make_member(role="editor")

        with (
            patch(
                "api.rbac.repo_query",
                new_callable=AsyncMock,
                return_value=[{"role": "editor"}],
            ),
            patch(
                "api.routers.sources.repo_query",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces/workspace:ws1/sources",
                    data={"type": "upload", "async_processing": "true"},
                    files=[_large_file_bytes(51)],
                    headers=_auth_headers(sub="user_editor"),
                )

        assert response.status_code == 413
        assert "50MB" in response.json()["detail"] or "50" in response.json()["detail"]


class TestDuplicateFileWarning:
    """Same filename uploaded twice to same workspace -> duplicate warning."""

    @pytest.mark.asyncio
    async def test_duplicate_file_warning(self, test_app, mock_jwks):
        """Same filename in workspace -> returns 409 with duplicate warning."""
        editor_member = _make_member(role="editor")

        existing_source = {
            "id": "source:existing",
            "title": "test.txt",
            "asset": {"file_path": "/uploads/test.txt", "url": None},
        }

        with (
            patch(
                "api.rbac.repo_query",
                new_callable=AsyncMock,
                return_value=[{"role": "editor"}],
            ),
            patch(
                "api.routers.sources.repo_query",
                new_callable=AsyncMock,
                return_value=[existing_source],
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces/workspace:ws1/sources",
                    data={"type": "upload", "async_processing": "true"},
                    files=[_small_file_bytes(filename="test.txt")],
                    headers=_auth_headers(sub="user_editor"),
                )

        assert response.status_code == 409
        body = response.json()
        assert "duplicate" in body["detail"].lower()


class TestUploadWithoutEditorRole:
    """Viewer uploads -> 403."""

    @pytest.mark.asyncio
    async def test_upload_without_editor_role(self, test_app, mock_jwks):
        """Viewer tries upload -> 403."""
        viewer_member = _make_member(
            user_id="user_viewer",
            role="viewer",
        )

        with patch(
            "api.rbac.repo_query",
            new_callable=AsyncMock,
            return_value=[{"role": "viewer"}],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces/workspace:ws1/sources",
                    data={"type": "text", "content": "hello"},
                    headers=_auth_headers(sub="user_viewer"),
                )

        assert response.status_code == 403


class TestRagAnythingImportFailureFallback:
    """RAGAnything not installed -> falls back to content-core gracefully."""

    @pytest.mark.asyncio
    async def test_raganything_import_failure_fallback(self):
        """RAGAnything not installed -> raganything_extract returns None for PDF."""
        from open_notebook.services.ingestion_service import raganything_extract

        with patch(
            "open_notebook.services.ingestion_service._try_import_raganything",
            return_value=None,
        ):
            result = await raganything_extract("/path/to/doc.pdf")

        assert result is None


# =============================================================================
# ADVERSARIAL CASES
# =============================================================================


class TestUploadToNonexistentWorkspace:
    """Upload to non-member workspace -> 403."""

    @pytest.mark.asyncio
    async def test_upload_to_nonexistent_workspace(self, test_app, mock_jwks):
        """Upload to workspace where user has no membership -> 403."""
        with patch(
            "api.rbac.repo_query",
            new_callable=AsyncMock,
            return_value=[],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/workspaces/workspace:nonexistent/sources",
                    data={"type": "text", "content": "hello"},
                    headers=_auth_headers(sub="user_attacker"),
                )

        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
