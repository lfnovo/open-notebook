from typing import Any

from open_notebook.database.repository import repo_query


class SearchRepository:
    """Named search queries used by domain-level search helpers."""

    @staticmethod
    async def text_search(
        keyword: str,
        results: int,
        *,
        source: bool,
        note: bool,
    ) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT *
            FROM fn::text_search($keyword, $results, $source, $note)
            """,
            {"keyword": keyword, "results": results, "source": source, "note": note},
        )

    @staticmethod
    async def vector_search(
        embed: list[float],
        results: int,
        *,
        source: bool,
        note: bool,
        minimum_score: float,
    ) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT * FROM fn::vector_search($embed, $results, $source, $note, $minimum_score)
            """,
            {
                "embed": embed,
                "results": results,
                "source": source,
                "note": note,
                "minimum_score": minimum_score,
            },
        )

    @staticmethod
    async def graph_entry_nodes(
        keyword: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT id, name, type, description, source_id, math::max([search::score(1), search::score(2)]) AS relevance
            FROM kg_entity
            WHERE name @1@ $keyword OR description @2@ $keyword
            GROUP BY id, name, type, description, source_id
            ORDER BY relevance DESC
            LIMIT $limit
            """,
            {"keyword": keyword, "limit": limit},
        )

    @staticmethod
    async def graph_subgraphs(entry_ids: list[Any]) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT
                id,
                name,
                type,
                description,
                source_id,
                ->kg_relation->kg_entity.{id, name, type, description} AS outbound_nodes,
                ->kg_relation.{type, description} AS outbound_edges,
                <-kg_relation<-kg_entity.{id, name, type, description} AS inbound_nodes,
                <-kg_relation.{type, description} AS inbound_edges
            FROM $entry_ids
            """,
            {"entry_ids": entry_ids},
        )
