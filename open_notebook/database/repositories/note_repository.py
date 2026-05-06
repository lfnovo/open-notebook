from typing import Any, Optional

from open_notebook.database.repository import ensure_record_id, repo_query


class NoteRepository:
    """Named note queries used by API routers and services."""

    @staticmethod
    async def notebook_for_note(note_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT out AS notebook FROM artifact
            WHERE in = $note_id
            LIMIT 1
            FETCH notebook
            """,
            {"note_id": ensure_record_id(note_id)},
        )
        if not result:
            return None

        notebook = result[0].get("notebook")
        if isinstance(notebook, list):
            return notebook[0] if notebook else None
        if isinstance(notebook, dict):
            return notebook
        return None
