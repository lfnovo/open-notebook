"""Linking a source that is already in the notebook must not add a second edge.

`reference` edges are created as `source->reference->notebook`, so `in` is the
source and `out` is the notebook. The existence check has to look them up the
same way, or it never matches and every call adds another edge.
"""

import re
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class FakeReferences:
    """Minimal stand-in for the `reference` edge table."""

    def __init__(self):
        self.edges: list[dict[str, str]] = []

    async def query(self, query, vars=None):
        vars = {k: str(v) for k, v in (vars or {}).items()}
        if query.startswith("RELATE"):
            self.edges.append({"in": vars["source_id"], "out": vars["notebook_id"]})
            return []
        conditions = re.findall(r"\b(in|out) = \$(\w+)", query)
        return [
            edge
            for edge in self.edges
            if all(edge[field] == vars[param] for field, param in conditions)
        ]


def test_linking_twice_creates_one_reference(client):
    references = FakeReferences()
    with (
        patch("api.routers.notebooks.Notebook.get", new=AsyncMock()),
        patch("api.routers.notebooks.Source.get", new=AsyncMock()),
        patch("api.routers.notebooks.repo_query", new=references.query),
    ):
        for _ in range(2):
            response = client.post("/api/notebooks/notebook:n1/sources/source:s1")
            assert response.status_code == 200

    assert references.edges == [{"in": "source:s1", "out": "notebook:n1"}]
