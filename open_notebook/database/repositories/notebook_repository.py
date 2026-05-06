from typing import Any, Optional

from open_notebook.database.repository import (
    ensure_record_id,
    repo_query,
    repo_transaction,
)


class NotebookRepository:
    """Named notebook queries used by API services and routers."""

    @staticmethod
    async def list_notebooks(
        *,
        user_id: Optional[str],
        archived: Optional[bool],
        order_by: str,
        public_only: bool = False,
        team_ids: Optional[list[str]] = None,
        workspace_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if public_only or not user_id:
            visibility_filter = "(visibility = 'public')"
            params: dict[str, Any] = {}
        else:
            access_conditions = ["(owner_id = $user_id)", "(visibility = 'public')"]
            params = {
                "user_id": ensure_record_id(user_id),
                "user_id_string": str(user_id),
            }
            share_target_conditions = ["(target_type = 'user' AND target_id = $user_id_string)"]
            if team_ids:
                share_target_conditions.append(
                    "(target_type = 'team' AND target_id IN $team_ids)"
                )
                params["team_ids"] = team_ids
            access_conditions.append(
                "type::string(id) IN (SELECT VALUE resource_id FROM share_grant "
                "WHERE resource_type = 'notebook' AND permission IN ['read', 'write', 'owner'] "
                f"AND ({' OR '.join(share_target_conditions)}))"
            )
            access_conditions.append(
                "workspace_id IN (SELECT VALUE id FROM workspace "
                "WHERE owner_id = $user_id OR team_id IN ("
                "SELECT VALUE team FROM team_member WHERE user = $user_id AND status = 'active'"
                "))"
            )
            visibility_filter = " OR ".join(access_conditions)

        workspace_filter = ""
        if workspace_id:
            workspace_filter = " AND workspace_id = $workspace_id"
            params["workspace_id"] = ensure_record_id(workspace_id)

        query = f"""
            SELECT *,
            (SELECT VALUE username FROM app_user WHERE id = $parent.owner_id LIMIT 1)[0] as creator_username,
            count(<-reference.in) as source_count,
            count(<-artifact.in) as note_count
            FROM notebook
            WHERE ({visibility_filter}){workspace_filter}
            ORDER BY {order_by}
        """

        result = await repo_query(query, params)
        if archived is not None:
            result = [nb for nb in result if nb.get("archived") == archived]
        return result

    @staticmethod
    async def get_with_counts(notebook_id: str) -> Optional[dict[str, Any]]:
        query = """
            SELECT *,
            (SELECT VALUE username FROM app_user WHERE id = $parent.owner_id LIMIT 1)[0] as creator_username,
            count(<-reference.in) as source_count,
            count(<-artifact.in) as note_count
            FROM $notebook_id
        """
        result = await repo_query(query, {"notebook_id": ensure_record_id(notebook_id)})
        return result[0] if result else None

    @staticmethod
    async def source_rows(notebook_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT * OMIT source.full_text FROM (
                SELECT in AS source FROM reference WHERE out = $notebook_id
                FETCH source
            ) ORDER BY source.updated DESC
            """,
            {"notebook_id": ensure_record_id(notebook_id)},
        )

    @staticmethod
    async def note_rows(notebook_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT * OMIT note.content, note.embedding FROM (
                SELECT in AS note FROM artifact WHERE out = $notebook_id
                FETCH note
            ) ORDER BY note.updated DESC
            """,
            {"notebook_id": ensure_record_id(notebook_id)},
        )

    @staticmethod
    async def chat_session_rows(notebook_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT * FROM (
                SELECT <-chat_session AS chat_session
                FROM refers_to
                WHERE out = $notebook_id
                FETCH chat_session
            )
            ORDER BY chat_session.updated DESC
            """,
            {"notebook_id": ensure_record_id(notebook_id)},
        )

    @staticmethod
    async def note_count(notebook_id: str) -> int:
        result = await repo_query(
            "SELECT count() AS count FROM artifact WHERE out = $notebook_id GROUP ALL",
            {"notebook_id": ensure_record_id(notebook_id)},
        )
        return result[0]["count"] if result else 0

    @staticmethod
    async def source_reference_counts(notebook_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT
                id,
                count(->reference[WHERE out != $notebook_id].out) AS assigned_others
            FROM (SELECT VALUE <-reference.in AS sources FROM $notebook_id)[0]
            """,
            {"notebook_id": ensure_record_id(notebook_id)},
        )

    @staticmethod
    async def source_reference_count(notebook_id: str) -> int:
        result = await repo_query(
            "SELECT count() AS count FROM reference WHERE out = $notebook_id GROUP ALL",
            {"notebook_id": ensure_record_id(notebook_id)},
        )
        return result[0]["count"] if result else 0

    @staticmethod
    async def delete_artifacts(notebook_id: str) -> None:
        await repo_query(
            "DELETE artifact WHERE out = $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)},
        )

    @staticmethod
    async def delete_references(notebook_id: str) -> None:
        await repo_query(
            "DELETE reference WHERE out = $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)},
        )

    @staticmethod
    async def delete_notebook_records_transaction(
        notebook_id: str,
        *,
        exclusive_source_ids: list[str],
        include_knowledge_graph: bool,
    ) -> None:
        exclusive_source_record_ids = [
            ensure_record_id(source_id) for source_id in exclusive_source_ids
        ]
        exclusive_source_id_strings = [
            str(source_id) for source_id in exclusive_source_ids
        ]

        kg_statements = ""
        if include_knowledge_graph:
            kg_statements = """
            DELETE kg_entity WHERE source_id IN $exclusive_source_id_strings;
            DELETE kg_relation WHERE source_id IN $exclusive_source_id_strings;
            """

        await repo_transaction(
            f"""
            DELETE note WHERE id IN (SELECT VALUE in FROM artifact WHERE out = $notebook_id);
            DELETE artifact WHERE out = $notebook_id;
            DELETE reference WHERE out = $notebook_id;

            DELETE source_embedding WHERE source IN $exclusive_source_ids;
            DELETE source_insight WHERE source IN $exclusive_source_ids;
            {kg_statements}
            DELETE source WHERE id IN $exclusive_source_ids;

            DELETE $notebook_id;
            """,
            {
                "notebook_id": ensure_record_id(notebook_id),
                "exclusive_source_ids": exclusive_source_record_ids,
                "exclusive_source_id_strings": exclusive_source_id_strings,
            },
        )

    @staticmethod
    async def source_reference_exists(notebook_id: str, source_id: str) -> bool:
        result = await repo_query(
            "SELECT id FROM reference WHERE out = $notebook_id AND in = $source_id LIMIT 1",
            {
                "notebook_id": ensure_record_id(notebook_id),
                "source_id": ensure_record_id(source_id),
            },
        )
        return bool(result)

    @staticmethod
    async def link_source(notebook_id: str, source_id: str) -> None:
        if await NotebookRepository.source_reference_exists(notebook_id, source_id):
            return

        await repo_query(
            "RELATE $source_id->reference->$notebook_id",
            {
                "notebook_id": ensure_record_id(notebook_id),
                "source_id": ensure_record_id(source_id),
            },
        )

    @staticmethod
    async def unlink_source(notebook_id: str, source_id: str) -> None:
        await repo_query(
            "DELETE FROM reference WHERE out = $notebook_id AND in = $source_id",
            {
                "notebook_id": ensure_record_id(notebook_id),
                "source_id": ensure_record_id(source_id),
            },
        )
