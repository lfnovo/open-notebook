"""Repo review domain model.

A Review records one run of the repo-review feature: the user's theme/question,
the local repo path, the async job that runs it, and — once complete — the verdict
summary and a pointer to the AI Note holding the full report.
"""

from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field

from open_notebook.database.repository import repo_query
from open_notebook.domain.base import ObjectModel


class Review(ObjectModel):
    """A single repo-review run and its result."""

    table_name: ClassVar[str] = "review"
    # These may legitimately be None and must round-trip to the DB as such.
    nullable_fields: ClassVar[set[str]] = {
        "notebook_id",
        "command_id",
        "report_note_id",
        "summary",
        "error_message",
    }

    theme: str
    repo_path: str
    notebook_id: Optional[str] = None
    status: str = "queued"  # queued | running | completed | failed
    command_id: Optional[str] = None
    report_note_id: Optional[str] = None
    # Per-verdict counts, e.g. {"follows": 3, "partial": 1, "violates": 2, "not-found": 0}
    summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    @classmethod
    async def get_recent(cls, notebook_id: Optional[str] = None, limit: int = 50) -> List["Review"]:
        """List reviews, newest first, optionally scoped to a notebook."""
        if notebook_id:
            result = await repo_query(
                "SELECT * FROM review WHERE notebook_id = $nb ORDER BY created DESC LIMIT $limit",
                {"nb": notebook_id, "limit": limit},
            )
        else:
            result = await repo_query(
                "SELECT * FROM review ORDER BY created DESC LIMIT $limit",
                {"limit": limit},
            )
        return [cls(**row) for row in result]
