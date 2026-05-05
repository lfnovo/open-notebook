from __future__ import annotations

from typing import Any

from open_notebook.database.repository import (
    ensure_record_id,
    repo_query,
    repo_transaction,
)


class TeamAllowlistRepository:
    """Named team model and transformation allowlist queries."""

    @staticmethod
    async def list_team_models(team_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT * FROM team_model
            WHERE team = $team_id
            ORDER BY created ASC
            FETCH model
            """,
            {"team_id": ensure_record_id(team_id)},
        )

    @staticmethod
    async def replace_team_models(
        team_id: str,
        model_ids: list[str],
        actor_id: str,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "team_id": ensure_record_id(team_id),
            "created_by": ensure_record_id(actor_id),
        }
        create_lines = []
        for index, model_id in enumerate(model_ids):
            param_name = f"model_id_{index}"
            params[param_name] = ensure_record_id(model_id)
            create_lines.append(
                f"""
                CREATE team_model SET
                    team = $team_id,
                    model = ${param_name},
                    created_by = $created_by,
                    created = time::now();
                """
            )

        result = await repo_transaction(
            f"""
            DELETE team_model WHERE team = $team_id;
            {''.join(create_lines)}
            SELECT * FROM team_model
            WHERE team = $team_id
            ORDER BY created ASC
            FETCH model;
            """,
            params,
        )
        return result[-1] if result else []

    @staticmethod
    async def list_team_transformations(team_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT * FROM team_transformation
            WHERE team = $team_id
            ORDER BY created ASC
            FETCH transformation
            """,
            {"team_id": ensure_record_id(team_id)},
        )

    @staticmethod
    async def replace_team_transformations(
        team_id: str,
        transformation_ids: list[str],
        actor_id: str,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "team_id": ensure_record_id(team_id),
            "created_by": ensure_record_id(actor_id),
        }
        create_lines = []
        for index, transformation_id in enumerate(transformation_ids):
            param_name = f"transformation_id_{index}"
            params[param_name] = ensure_record_id(transformation_id)
            create_lines.append(
                f"""
                CREATE team_transformation SET
                    team = $team_id,
                    transformation = ${param_name},
                    created_by = $created_by,
                    created = time::now();
                """
            )

        result = await repo_transaction(
            f"""
            DELETE team_transformation WHERE team = $team_id;
            {''.join(create_lines)}
            SELECT * FROM team_transformation
            WHERE team = $team_id
            ORDER BY created ASC
            FETCH transformation;
            """,
            params,
        )
        return result[-1] if result else []
