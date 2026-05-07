from typing import Any

from open_notebook.database.repository import repo_query


def _record_ref(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        table = value.get("tb") or value.get("table")
        record_id = _record_ref(value.get("id"))
        if table and record_id:
            return record_id if record_id.startswith(f"{table}:") else f"{table}:{record_id}"
        return record_id
    return str(value)


def _score(row: dict[str, Any]) -> float:
    value = row.get("similarity")
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _first_scalar(value: Any) -> Any:
    if isinstance(value, list):
        return next((item for item in value if item is not None), None)
    return value


def _aggregate_vector_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    match_scores: dict[str, list[tuple[float, str]]] = {}

    for row in rows:
        parent_id = _record_ref(row.get("parent_id") or row.get("id"))
        if not parent_id:
            continue

        content = _first_scalar(row.get("content"))
        if content is not None:
            content = str(content).strip()

        existing = grouped.get(parent_id)
        if existing is None or _score(row) > _score(existing):
            grouped[parent_id] = {
                "id": _record_ref(row.get("id")) or parent_id,
                "parent_id": parent_id,
                "title": _first_scalar(row.get("title")),
                "similarity": _score(row),
            }

        if content:
            match_scores.setdefault(parent_id, []).append((_score(row), content))

    results = sorted(grouped.values(), key=_score, reverse=True)
    for result in results:
        scored_matches = sorted(
            match_scores.get(result["parent_id"], []),
            key=lambda item: item[0],
            reverse=True,
        )
        seen: set[str] = set()
        matches: list[str] = []
        for _, match in scored_matches:
            if match not in seen:
                seen.add(match)
                matches.append(match)
        result["matches"] = matches

    return results[:limit]


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
        params = {
            "embed": embed,
            "results": results,
            "minimum_score": minimum_score,
        }
        rows: list[dict[str, Any]] = []

        if source:
            rows.extend(
                await repo_query(
                    """
                    SELECT
                        source.id AS id,
                        source.title AS title,
                        content,
                        source.id AS parent_id,
                        vector::similarity::cosine(embedding, $embed) AS similarity
                    FROM source_embedding
                    WHERE embedding != none
                        AND array::len(embedding) = array::len($embed)
                        AND vector::similarity::cosine(embedding, $embed) >= $minimum_score
                    ORDER BY similarity DESC
                    LIMIT $results
                    """,
                    params,
                )
            )
            rows.extend(
                await repo_query(
                    """
                    SELECT
                        id,
                        insight_type + ' - ' + (source.title OR '') AS title,
                        content,
                        source.id AS parent_id,
                        vector::similarity::cosine(embedding, $embed) AS similarity
                    FROM source_insight
                    WHERE embedding != none
                        AND array::len(embedding) = array::len($embed)
                        AND vector::similarity::cosine(embedding, $embed) >= $minimum_score
                    ORDER BY similarity DESC
                    LIMIT $results
                    """,
                    params,
                )
            )

        if note:
            rows.extend(
                await repo_query(
                    """
                    SELECT
                        id,
                        title,
                        content,
                        id AS parent_id,
                        vector::similarity::cosine(embedding, $embed) AS similarity
                    FROM note
                    WHERE embedding != none
                        AND array::len(embedding) = array::len($embed)
                        AND vector::similarity::cosine(embedding, $embed) >= $minimum_score
                    ORDER BY similarity DESC
                    LIMIT $results
                    """,
                    params,
                )
            )

        return _aggregate_vector_rows(rows, results)

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
