"""
Unit tests for Workspace and WorkspaceMember domain models.

Tests cover validation logic, CRUD operations (mocked), cascade delete,
and edge cases without requiring a running database.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from open_notebook.domain.workspace import Workspace, WorkspaceMember
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError


# ============================================================================
# TEST SUITE 1: Workspace Creation & Validation
# ============================================================================


class TestWorkspaceCreation:
    """Test suite for Workspace model creation and validation."""

    def test_create_workspace(self):
        """Create workspace with name, visibility, owner_id -> valid instance."""
        workspace = Workspace(
            name="Test Workspace",
            visibility="private",
            owner_id="user_1",
        )
        assert workspace.name == "Test Workspace"
        assert workspace.visibility == "private"
        assert workspace.owner_id == "user_1"
        assert workspace.description is None
        assert workspace.org_id is None

    def test_create_workspace_with_all_fields(self):
        """Create workspace with all optional fields populated."""
        workspace = Workspace(
            name="Full Workspace",
            description="A thorough description",
            visibility="shared",
            owner_id="user_1",
            org_id="org_42",
        )
        assert workspace.description == "A thorough description"
        assert workspace.org_id == "org_42"

    def test_create_workspace_invalid_visibility(self):
        """visibility='public' -> validation error."""
        with pytest.raises(InvalidInputError, match="Visibility must be"):
            Workspace(
                name="Bad Workspace",
                visibility="public",
                owner_id="user_1",
            )

    def test_create_workspace_empty_name(self):
        """Empty name -> validation error."""
        with pytest.raises(InvalidInputError, match="Workspace name cannot be empty"):
            Workspace(name="", visibility="private", owner_id="user_1")

    def test_create_workspace_whitespace_name(self):
        """Whitespace-only name -> validation error."""
        with pytest.raises(InvalidInputError, match="Workspace name cannot be empty"):
            Workspace(name="   ", visibility="private", owner_id="user_1")

    def test_create_workspace_all_visibility_values(self):
        """All three valid visibility values are accepted."""
        for visibility in ("private", "shared", "community"):
            workspace = Workspace(name="Test", visibility=visibility, owner_id="user_1")
            assert workspace.visibility == visibility

    def test_create_workspace_empty_owner_id(self):
        """Empty owner_id -> validation error."""
        with pytest.raises(InvalidInputError, match="Owner ID cannot be empty"):
            Workspace(name="Test", visibility="private", owner_id="")


# ============================================================================
# TEST SUITE 2: Workspace CRUD with Mocked DB
# ============================================================================


class TestWorkspaceCRUD:
    """Test suite for Workspace save/get/delete using mocked repository."""

    @pytest.mark.asyncio
    async def test_save_workspace_creates_record(self):
        """Workspace.save() calls repo_create for new records."""
        workspace = Workspace(
            name="New Workspace", visibility="private", owner_id="user_1"
        )

        with patch(
            "open_notebook.domain.base.repo_create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = [
                {
                    "id": "workspace:abc123",
                    "name": "New Workspace",
                    "visibility": "private",
                    "owner_id": "user_1",
                    "created": "2026-04-12T00:00:00",
                    "updated": "2026-04-12T00:00:00",
                }
            ]
            await workspace.save()
            mock_create.assert_called_once()
            assert workspace.id == "workspace:abc123"

    @pytest.mark.asyncio
    async def test_save_workspace_updates_existing(self):
        """Workspace.save() calls repo_update for existing records."""
        workspace = Workspace(
            id="workspace:abc123",
            name="Updated Workspace",
            visibility="shared",
            owner_id="user_1",
            created="2026-04-12T00:00:00",
        )

        with patch(
            "open_notebook.domain.base.repo_update", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = [
                {
                    "id": "workspace:abc123",
                    "name": "Updated Workspace",
                    "visibility": "shared",
                    "owner_id": "user_1",
                    "created": "2026-04-12T00:00:00",
                    "updated": "2026-04-12T00:00:00",
                }
            ]
            await workspace.save()
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_workspace_without_id_raises(self):
        """Deleting workspace without ID raises InvalidInputError."""
        workspace = Workspace(name="Test", visibility="private", owner_id="user_1")
        with pytest.raises(InvalidInputError, match="Cannot delete"):
            await workspace.delete()


# ============================================================================
# TEST SUITE 3: WorkspaceMember
# ============================================================================


class TestWorkspaceMember:
    """Test suite for WorkspaceMember model."""

    def test_add_member(self):
        """Create WorkspaceMember with valid fields."""
        member = WorkspaceMember(
            workspace_id="workspace:abc123",
            user_id="user_2",
            role="editor",
        )
        assert member.workspace_id == "workspace:abc123"
        assert member.user_id == "user_2"
        assert member.role == "editor"

    def test_member_invalid_role(self):
        """Invalid role -> validation error."""
        with pytest.raises(InvalidInputError, match="Role must be"):
            WorkspaceMember(
                workspace_id="workspace:abc123",
                user_id="user_2",
                role="admin",
            )

    def test_member_all_valid_roles(self):
        """All three valid roles are accepted."""
        for role in ("owner", "editor", "viewer"):
            member = WorkspaceMember(
                workspace_id="workspace:abc123",
                user_id="user_2",
                role=role,
            )
            assert member.role == role

    def test_member_empty_user_id(self):
        """Empty user_id -> validation error."""
        with pytest.raises(InvalidInputError, match="User ID cannot be empty"):
            WorkspaceMember(
                workspace_id="workspace:abc123",
                user_id="",
                role="editor",
            )

    def test_member_empty_workspace_id(self):
        """Empty workspace_id -> validation error."""
        with pytest.raises(InvalidInputError, match="Workspace ID cannot be empty"):
            WorkspaceMember(
                workspace_id="",
                user_id="user_2",
                role="editor",
            )

    @pytest.mark.asyncio
    async def test_save_member(self):
        """WorkspaceMember.save() calls repo_create for new records."""
        member = WorkspaceMember(
            workspace_id="workspace:abc123",
            user_id="user_2",
            role="editor",
        )

        with patch(
            "open_notebook.domain.base.repo_create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = [
                {
                    "id": "workspace_member:xyz789",
                    "workspace_id": "workspace:abc123",
                    "user_id": "user_2",
                    "role": "editor",
                    "created": "2026-04-12T00:00:00",
                    "updated": "2026-04-12T00:00:00",
                }
            ]
            await member.save()
            mock_create.assert_called_once()
            assert member.id == "workspace_member:xyz789"


# ============================================================================
# TEST SUITE 4: WorkspaceMember Query Methods
# ============================================================================


class TestWorkspaceMemberQueries:
    """Test suite for WorkspaceMember class-level query methods."""

    @pytest.mark.asyncio
    async def test_get_for_user(self):
        """get_for_user returns all memberships for a user."""
        mock_results = [
            {
                "id": "workspace_member:1",
                "workspace_id": "workspace:a",
                "user_id": "user_1",
                "role": "owner",
                "created": "2026-04-12T00:00:00",
                "updated": "2026-04-12T00:00:00",
            },
            {
                "id": "workspace_member:2",
                "workspace_id": "workspace:b",
                "user_id": "user_1",
                "role": "viewer",
                "created": "2026-04-12T00:00:00",
                "updated": "2026-04-12T00:00:00",
            },
        ]

        with patch(
            "open_notebook.domain.workspace.repo_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = mock_results
            members = await WorkspaceMember.get_for_user("user_1")
            assert len(members) == 2
            assert members[0].role == "owner"
            assert members[1].role == "viewer"
            mock_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_for_workspace(self):
        """get_for_workspace returns all members of a workspace."""
        mock_results = [
            {
                "id": "workspace_member:1",
                "workspace_id": "workspace:a",
                "user_id": "user_1",
                "role": "owner",
                "created": "2026-04-12T00:00:00",
                "updated": "2026-04-12T00:00:00",
            },
            {
                "id": "workspace_member:2",
                "workspace_id": "workspace:a",
                "user_id": "user_2",
                "role": "editor",
                "created": "2026-04-12T00:00:00",
                "updated": "2026-04-12T00:00:00",
            },
        ]

        with patch(
            "open_notebook.domain.workspace.repo_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = mock_results
            members = await WorkspaceMember.get_for_workspace("workspace:a")
            assert len(members) == 2
            assert members[0].user_id == "user_1"
            assert members[1].user_id == "user_2"
            mock_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_members_returns_both(self):
        """Workspace with 2 members -> returns both via get_for_workspace."""
        mock_results = [
            {
                "id": "workspace_member:1",
                "workspace_id": "workspace:ws1",
                "user_id": "user_owner",
                "role": "owner",
                "created": "2026-04-12T00:00:00",
                "updated": "2026-04-12T00:00:00",
            },
            {
                "id": "workspace_member:2",
                "workspace_id": "workspace:ws1",
                "user_id": "user_editor",
                "role": "editor",
                "created": "2026-04-12T00:00:00",
                "updated": "2026-04-12T00:00:00",
            },
        ]

        with patch(
            "open_notebook.domain.workspace.repo_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = mock_results
            members = await WorkspaceMember.get_for_workspace("workspace:ws1")
            assert len(members) == 2


# ============================================================================
# TEST SUITE 5: Cascade Delete
# ============================================================================


class TestWorkspaceCascadeDelete:
    """Test cascade delete behavior for Workspace."""

    @pytest.mark.asyncio
    async def test_cascade_delete(self):
        """Delete workspace -> sources, notes, chat sessions, members deleted."""
        workspace = Workspace(
            id="workspace:ws1",
            name="Doomed Workspace",
            visibility="private",
            owner_id="user_1",
            created="2026-04-12T00:00:00",
        )

        with (
            patch(
                "open_notebook.domain.workspace.repo_query", new_callable=AsyncMock
            ) as mock_query,
            patch(
                "open_notebook.domain.base.repo_delete", new_callable=AsyncMock
            ) as mock_delete,
        ):
            mock_query.return_value = []
            mock_delete.return_value = True

            result = await workspace.delete()
            assert result is True

            # Verify cascade queries were executed (sources, notes, chat sessions, members)
            query_calls = mock_query.call_args_list
            assert len(query_calls) >= 4, (
                f"Expected at least 4 cascade delete queries, got {len(query_calls)}"
            )


# ============================================================================
# TEST SUITE 6: workspace_id on Existing Models
# ============================================================================


class TestWorkspaceIdOnExistingModels:
    """Test that existing models accept workspace_id field."""

    def test_source_with_workspace_id(self):
        """Source saves with workspace_id."""
        from open_notebook.domain.notebook import Source

        source = Source(title="doc", workspace_id="workspace:ws1")
        assert source.workspace_id == "workspace:ws1"

    def test_source_without_workspace_id(self):
        """Source works without workspace_id (backward compatible)."""
        from open_notebook.domain.notebook import Source

        source = Source(title="doc")
        assert source.workspace_id is None

    def test_note_with_workspace_id(self):
        """Note accepts workspace_id."""
        from open_notebook.domain.notebook import Note

        note = Note(title="test note", content="content", workspace_id="workspace:ws1")
        assert note.workspace_id == "workspace:ws1"

    def test_chat_session_with_workspace_id(self):
        """ChatSession accepts workspace_id."""
        from open_notebook.domain.notebook import ChatSession

        session = ChatSession(title="test", workspace_id="workspace:ws1")
        assert session.workspace_id == "workspace:ws1"

    def test_source_embedding_with_workspace_id(self):
        """SourceEmbedding accepts workspace_id."""
        from open_notebook.domain.notebook import SourceEmbedding

        embedding = SourceEmbedding(content="chunk", workspace_id="workspace:ws1")
        assert embedding.workspace_id == "workspace:ws1"


# ============================================================================
# TEST SUITE 7: Duplicate Membership
# ============================================================================


class TestDuplicateMembership:
    """Test duplicate membership handling."""

    @pytest.mark.asyncio
    async def test_duplicate_membership(self):
        """Same user+workspace twice -> DatabaseOperationError from DB constraint."""
        member = WorkspaceMember(
            workspace_id="workspace:abc123",
            user_id="user_2",
            role="editor",
        )

        with patch(
            "open_notebook.domain.base.repo_create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("Database record already exists")
            with pytest.raises(DatabaseOperationError):
                await member.save()


# ============================================================================
# TEST SUITE 8: Adversarial Cases
# ============================================================================


class TestWorkspaceAdversarial:
    """Adversarial input tests."""

    def test_workspace_id_injection(self):
        """workspace_id with injection chars -> safely handled via validation."""
        from open_notebook.domain.notebook import Source

        # The workspace_id is stored as a string and passed to SurrealDB
        # as a parameter (not interpolated), so injection is neutralized.
        # The model should accept it without error — SurrealDB parameterized
        # queries handle the rest.
        source = Source(
            title="test",
            workspace_id="workspace:123; DELETE workspace",
        )
        assert source.workspace_id == "workspace:123; DELETE workspace"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
