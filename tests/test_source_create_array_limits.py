"""
Tests for max_length on SourceCreate.notebooks/transformations
(api/models.py).

Both are iterated with a per-item DB lookup (Notebook.get()/
Transformation.get()) in api/routers/sources.py's create_source() - an
unbounded array let a caller amplify a single request into an arbitrarily
large number of sequential DB round trips.
"""

import pytest
from pydantic import ValidationError

from api.models import SourceCreate


def make_ids(n, prefix):
    return [f"{prefix}:{i}" for i in range(n)]


class TestNotebooksMaxLength:
    def test_accepts_up_to_50_notebooks(self):
        request = SourceCreate(type="text", content="hi", notebooks=make_ids(50, "notebook"))
        assert request.notebooks is not None
        assert len(request.notebooks) == 50

    def test_rejects_51_notebooks(self):
        with pytest.raises(ValidationError):
            SourceCreate(type="text", content="hi", notebooks=make_ids(51, "notebook"))

    def test_none_notebooks_still_allowed(self):
        # Pre-existing behavior (validate_notebook_fields): None normalizes
        # to an empty list, unrelated to the max_length addition.
        request = SourceCreate(type="text", content="hi", notebooks=None)
        assert request.notebooks == []

    def test_empty_list_still_allowed(self):
        request = SourceCreate(type="text", content="hi", notebooks=[])
        assert request.notebooks == []


class TestTransformationsMaxLength:
    def test_accepts_up_to_50_transformations(self):
        request = SourceCreate(
            type="text", content="hi", transformations=make_ids(50, "transformation")
        )
        assert request.transformations is not None
        assert len(request.transformations) == 50

    def test_rejects_51_transformations(self):
        with pytest.raises(ValidationError):
            SourceCreate(
                type="text", content="hi", transformations=make_ids(51, "transformation")
            )

    def test_default_is_empty_list(self):
        request = SourceCreate(type="text", content="hi")
        assert request.transformations == []


class TestFormParsingReturns422:
    """The multipart form path builds SourceCreate manually in
    parse_source_form_data(), so pydantic's ValidationError doesn't go
    through FastAPI's request-validation handler — without an explicit
    catch it surfaced as a 500. These hit the real endpoint and assert
    the client gets a clean 422 instead (found in v1.11 release testing).
    """

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from api.main import app

        return TestClient(app)

    def test_51_notebooks_via_form_returns_422(self, client):
        import json as _json

        response = client.post(
            "/api/sources",
            data={
                "type": "text",
                "content": "probe",
                "notebooks": _json.dumps(make_ids(51, "notebook")),
            },
        )
        assert response.status_code == 422
        assert "Invalid source data" in response.json()["detail"]

    def test_invalid_notebooks_json_returns_422(self, client):
        response = client.post(
            "/api/sources",
            data={"type": "text", "content": "probe", "notebooks": "not-json["},
        )
        assert response.status_code == 422
        assert "notebooks" in response.json()["detail"]

    def test_invalid_transformations_json_returns_422(self, client):
        response = client.post(
            "/api/sources",
            data={"type": "text", "content": "probe", "transformations": "]bad"},
        )
        assert response.status_code == 422
        assert "transformations" in response.json()["detail"]
