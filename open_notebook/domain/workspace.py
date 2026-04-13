"""
Workspace and WorkspaceMember domain models.

Workspaces replace Notebooks as the primary organizational container.
A Workspace groups Sources, Notes, and ChatSessions under a shared
ownership and access-control boundary.
"""

from typing import ClassVar, List, Optional, Type, TypeVar

from loguru import logger
from pydantic import field_validator

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError

T = TypeVar("T", bound="Workspace")

VALID_VISIBILITIES = ("private", "shared", "community")
VALID_ROLES = ("owner", "editor", "viewer")


class Workspace(ObjectModel):
    table_name: ClassVar[str] = "workspace"
    nullable_fields: ClassVar[set[str]] = {"description", "org_id"}

    name: str
    description: Optional[str] = None
    visibility: str
    owner_id: str
    org_id: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise InvalidInputError("Workspace name cannot be empty")
        return value

    @field_validator("visibility")
    @classmethod
    def visibility_must_be_valid(cls, value: str) -> str:
        if value not in VALID_VISIBILITIES:
            raise InvalidInputError(
                f"Visibility must be one of: {', '.join(VALID_VISIBILITIES)}"
            )
        return value

    @field_validator("owner_id")
    @classmethod
    def owner_id_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise InvalidInputError("Owner ID cannot be empty")
        return value

    async def delete(self) -> bool:
        """
        Delete workspace with cascade deletion of related records.

        Removes all sources, notes, chat sessions, source embeddings,
        and workspace members that reference this workspace before
        deleting the workspace record itself.
        """
        if self.id is None:
            raise InvalidInputError("Cannot delete workspace without an ID")

        try:
            workspace_id = ensure_record_id(self.id)

            await repo_query(
                "DELETE source_embedding WHERE workspace_id = $workspace_id",
                {"workspace_id": workspace_id},
            )
            await repo_query(
                "DELETE source WHERE workspace_id = $workspace_id",
                {"workspace_id": workspace_id},
            )
            await repo_query(
                "DELETE note WHERE workspace_id = $workspace_id",
                {"workspace_id": workspace_id},
            )
            await repo_query(
                "DELETE chat_session WHERE workspace_id = $workspace_id",
                {"workspace_id": workspace_id},
            )
            await repo_query(
                "DELETE workspace_member WHERE workspace_id = $workspace_id",
                {"workspace_id": workspace_id},
            )

            result = await super().delete()

            try:
                from open_notebook.services.graph_service import GraphService

                await GraphService.delete_workspace(str(workspace_id))
            except Exception as e:
                logger.warning(
                    f"Failed to clean up graph for workspace {workspace_id}: {e}"
                )

            return result

        except Exception as error:
            logger.error(f"Error deleting workspace {self.id}: {error}")
            logger.exception(error)
            raise DatabaseOperationError(f"Failed to delete workspace: {error}")


class WorkspaceMember(ObjectModel):
    table_name: ClassVar[str] = "workspace_member"

    workspace_id: str
    user_id: str
    role: str

    @field_validator("workspace_id")
    @classmethod
    def workspace_id_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise InvalidInputError("Workspace ID cannot be empty")
        return value

    @field_validator("user_id")
    @classmethod
    def user_id_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise InvalidInputError("User ID cannot be empty")
        return value

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, value: str) -> str:
        if value not in VALID_ROLES:
            raise InvalidInputError(f"Role must be one of: {', '.join(VALID_ROLES)}")
        return value

    @classmethod
    async def get_for_user(cls, user_id: str) -> List["WorkspaceMember"]:
        """Return all workspace memberships for a given user."""
        if not user_id:
            raise InvalidInputError("User ID cannot be empty")
        try:
            results = await repo_query(
                "SELECT * FROM workspace_member WHERE user_id = $user_id",
                {"user_id": user_id},
            )
            return [cls(**row) for row in results] if results else []
        except Exception as error:
            logger.error(f"Error fetching memberships for user {user_id}: {error}")
            raise DatabaseOperationError(error)

    @classmethod
    async def get_for_workspace(cls, workspace_id: str) -> List["WorkspaceMember"]:
        """Return all members of a given workspace."""
        if not workspace_id:
            raise InvalidInputError("Workspace ID cannot be empty")
        try:
            record_id = ensure_record_id(workspace_id)
            results = await repo_query(
                "SELECT * FROM workspace_member WHERE workspace_id = $workspace_id",
                {"workspace_id": record_id},
            )
            return [cls(**row) for row in results] if results else []
        except Exception as error:
            logger.error(
                f"Error fetching members for workspace {workspace_id}: {error}"
            )
            raise DatabaseOperationError(error)
