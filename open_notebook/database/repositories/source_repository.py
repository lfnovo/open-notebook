from typing import Any, Optional

from open_notebook.database.repository import (
    ensure_record_id,
    repo_query,
    repo_transaction,
)


class SourceRepository:
    """Named source queries used by API services and routers."""

    @staticmethod
    async def list_sources(
        *,
        user_id: Optional[str],
        notebook_id: Optional[str],
        title_contains: Optional[str],
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        public_only: bool = False,
        team_ids: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
        conditions = []
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if public_only:
            conditions.append("visibility = 'public'")
        elif user_id:
            access_conditions = ["(owner_id = $user_id)", "(visibility = 'public')"]
            params["user_id"] = ensure_record_id(user_id)
            params["user_id_string"] = str(user_id)
            share_target_conditions = ["(target_type = 'user' AND target_id = $user_id_string)"]
            if team_ids:
                share_target_conditions.append(
                    "(target_type = 'team' AND target_id IN $team_ids)"
                )
                params["team_ids"] = team_ids
            access_conditions.append(
                "type::string(id) IN (SELECT VALUE resource_id FROM share_grant "
                "WHERE resource_type = 'source' AND permission IN ['read', 'write', 'owner'] "
                f"AND ({' OR '.join(share_target_conditions)}))"
            )
            conditions.append(f"({' OR '.join(access_conditions)})")
        else:
            conditions.append("visibility = 'public'")

        if title_contains:
            conditions.append(
                "string::contains(string::lowercase(title), string::lowercase($title_contains))"
            )
            params["title_contains"] = title_contains

        if notebook_id:
            conditions.append(
                "id IN (SELECT VALUE in FROM reference WHERE out = $notebook_id)"
            )
            params["notebook_id"] = ensure_record_id(notebook_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return await SourceRepository._list_query(where_clause, order_clause, params)

    @staticmethod
    async def get_list_row(source_id: str) -> Optional[dict[str, Any]]:
        result = await SourceRepository._list_query(
            "WHERE id = $sid",
            "",
            {"sid": ensure_record_id(source_id)},
            include_pagination=False,
        )
        return result[0] if result else None

    @staticmethod
    async def source_for_child_record(record_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT source FROM $record_id FETCH source
            """,
            {"record_id": ensure_record_id(record_id)},
        )
        if not result:
            return None
        return result[0].get("source")

    @staticmethod
    async def embedded_chunk_count(source_id: str) -> int:
        result = await repo_query(
            """
            SELECT count() AS chunks FROM source_embedding WHERE source = $source_id GROUP ALL
            """,
            {"source_id": ensure_record_id(source_id)},
        )
        return result[0]["chunks"] if result else 0

    @staticmethod
    async def has_knowledge_graph(source_id: str) -> bool:
        result = await repo_query(
            """
            SELECT count() AS entities FROM kg_entity WHERE source_id = $source_id GROUP ALL
            """,
            {"source_id": str(source_id)},
        )
        return bool(result and result[0]["entities"] > 0)

    @staticmethod
    async def insight_rows(source_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT * FROM source_insight WHERE source = $source_id
            """,
            {"source_id": ensure_record_id(source_id)},
        )

    @staticmethod
    async def referenced_notebook_ids(source_id: str) -> list[str]:
        refs = await repo_query(
            "SELECT VALUE out FROM reference WHERE in = $source_id",
            {"source_id": ensure_record_id(source_id)},
        )
        return [str(ref) for ref in refs or []]

    @staticmethod
    async def delete_related_records(
        source_id: str,
        *,
        include_knowledge_graph: bool,
    ) -> None:
        kg_statements = ""
        if include_knowledge_graph:
            kg_statements = """
            DELETE kg_entity WHERE source_id = $source_id_str;
            DELETE kg_relation WHERE source_id = $source_id_str;
            """

        await repo_transaction(
            f"""
            DELETE source_embedding WHERE source = $source_id;
            DELETE source_insight WHERE source = $source_id;
            {kg_statements}
            DELETE reference WHERE in = $source_id;
            """,
            {
                "source_id": ensure_record_id(source_id),
                "source_id_str": str(source_id),
            },
        )

    @staticmethod
    async def _list_query(
        where_clause: str,
        order_clause: str,
        params: dict[str, Any],
        *,
        include_pagination: bool = True,
    ) -> list[dict[str, Any]]:
        pagination_clause = "LIMIT $limit START $offset" if include_pagination else ""
        query = f"""
            SELECT id, asset, created, title, updated, topics, command, owner_id, visibility,
            (SELECT VALUE count() FROM source_insight WHERE source = $parent.id GROUP ALL)[0] OR 0 AS insights_count,
            (SELECT VALUE count() FROM reference WHERE in = $parent.id GROUP ALL)[0] OR 0 AS reference_count,
            (SELECT VALUE id FROM source_embedding WHERE source = $parent.id LIMIT 1) != [] AS embedded,
            (SELECT VALUE id FROM kg_entity WHERE source_id = type::string($parent.id) LIMIT 1) != [] AS kg_extracted
            FROM source
            {where_clause}
            {order_clause}
            {pagination_clause}
            FETCH command
        """
        return await repo_query(query, params)
