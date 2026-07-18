from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from open_notebook.domain.transformation import Transformation


def _client() -> TestClient:
    from api.main import app

    return TestClient(app)


def _transformation(model_id: str | None = None) -> Transformation:
    return Transformation(
        id="transformation:123",
        name="summary",
        title="Summary",
        description="Summarize the source",
        prompt="Summarize this",
        apply_default=False,
        model_id=model_id,
        created=datetime(2026, 1, 1, 12, 0, 0),
        updated=datetime(2026, 1, 1, 12, 0, 0),
    )


def _create_payload(model_id: str | None = None) -> dict:
    payload = {
        "name": "summary",
        "title": "Summary",
        "description": "Summarize the source",
        "prompt": "Summarize this",
        "apply_default": False,
    }
    if model_id is not None:
        payload["model_id"] = model_id
    return payload


def test_create_transformation_with_model_id_persists_and_reads_back():
    client = _client()
    saved_transformations: list[Transformation] = []

    async def capture_save(transformation: Transformation):
        saved_transformations.append(transformation)
        transformation.id = "transformation:created"
        transformation.created = datetime(2026, 1, 1, 12, 0, 0)
        transformation.updated = datetime(2026, 1, 1, 12, 0, 0)

    with (
        patch.object(
            Transformation, "save", autospec=True, side_effect=capture_save
        ),
        patch(
            "api.routers.transformations.Model.get",
            new_callable=AsyncMock,
            return_value=object(),
        ) as mock_model_get,
    ):
        response = client.post(
            "/api/transformations", json=_create_payload("model:local")
        )

    assert response.status_code == 200
    assert saved_transformations[0].model_id == "model:local"
    assert response.json()["model_id"] == "model:local"
    mock_model_get.assert_awaited_once_with("model:local")

    with patch(
        "api.routers.transformations.Transformation.get",
        new_callable=AsyncMock,
        return_value=saved_transformations[0],
    ):
        response = client.get("/api/transformations/transformation:created")

    assert response.status_code == 200
    assert response.json()["model_id"] == "model:local"


def test_execute_without_request_model_uses_stored_model():
    client = _client()
    transformation = _transformation(model_id="model:stored")

    with (
        patch(
            "api.routers.transformations.Transformation.get",
            new_callable=AsyncMock,
            return_value=transformation,
        ),
        patch(
            "api.routers.transformations.Model.get",
            new_callable=AsyncMock,
            return_value=object(),
        ) as mock_model_get,
        patch(
            "api.routers.transformations.transformation_graph.ainvoke",
            new_callable=AsyncMock,
            return_value={"output": "Stored model output"},
        ) as mock_ainvoke,
    ):
        response = client.post(
            "/api/transformations/execute",
            json={
                "transformation_id": transformation.id,
                "input_text": "Input text",
            },
        )

    assert response.status_code == 200
    assert response.json()["model_id"] == "model:stored"
    mock_model_get.assert_awaited_once_with("model:stored")
    assert (
        mock_ainvoke.call_args.kwargs["config"]["configurable"]["model_id"]
        == "model:stored"
    )


def test_execute_without_any_model_uses_default_transformation_model_fallback():
    client = _client()
    transformation = _transformation(model_id=None)

    with (
        patch(
            "api.routers.transformations.Transformation.get",
            new_callable=AsyncMock,
            return_value=transformation,
        ),
        patch(
            "api.routers.transformations.Model.get",
            new_callable=AsyncMock,
        ) as mock_model_get,
        patch(
            "api.routers.transformations.transformation_graph.ainvoke",
            new_callable=AsyncMock,
            return_value={"output": "Default model output"},
        ) as mock_ainvoke,
    ):
        response = client.post(
            "/api/transformations/execute",
            json={
                "transformation_id": transformation.id,
                "input_text": "Input text",
            },
        )

    assert response.status_code == 200
    assert response.json()["model_id"] is None
    mock_model_get.assert_not_awaited()
    assert mock_ainvoke.call_args.kwargs["config"]["configurable"]["model_id"] is None


def test_update_transformation_model_id_is_used_by_subsequent_execution():
    client = _client()
    transformation = _transformation(model_id="model:old")

    async def save_update(transformation: Transformation):
        transformation.updated = datetime(2026, 1, 1, 12, 5, 0)

    with (
        patch(
            "api.routers.transformations.Transformation.get",
            new_callable=AsyncMock,
            return_value=transformation,
        ),
        patch.object(
            Transformation, "save", autospec=True, side_effect=save_update
        ),
        patch(
            "api.routers.transformations.Model.get",
            new_callable=AsyncMock,
            return_value=object(),
        ) as mock_model_get,
        patch(
            "api.routers.transformations.transformation_graph.ainvoke",
            new_callable=AsyncMock,
            return_value={"output": "Updated model output"},
        ) as mock_ainvoke,
    ):
        update_response = client.put(
            f"/api/transformations/{transformation.id}",
            json={"model_id": "model:new"},
        )
        execute_response = client.post(
            "/api/transformations/execute",
            json={
                "transformation_id": transformation.id,
                "input_text": "Input text",
            },
        )

    assert update_response.status_code == 200
    assert update_response.json()["model_id"] == "model:new"
    assert execute_response.status_code == 200
    assert execute_response.json()["model_id"] == "model:new"
    # model:new is validated once at update time and looked up again at execute.
    assert mock_model_get.await_count == 2
    mock_model_get.assert_awaited_with("model:new")
    assert (
        mock_ainvoke.call_args.kwargs["config"]["configurable"]["model_id"]
        == "model:new"
    )


def test_execute_request_model_overrides_stored_model():
    client = _client()
    transformation = _transformation(model_id="model:stored")

    with (
        patch(
            "api.routers.transformations.Transformation.get",
            new_callable=AsyncMock,
            return_value=transformation,
        ),
        patch(
            "api.routers.transformations.Model.get",
            new_callable=AsyncMock,
            return_value=object(),
        ) as mock_model_get,
        patch(
            "api.routers.transformations.transformation_graph.ainvoke",
            new_callable=AsyncMock,
            return_value={"output": "Override output"},
        ) as mock_ainvoke,
    ):
        response = client.post(
            "/api/transformations/execute",
            json={
                "transformation_id": transformation.id,
                "input_text": "Input text",
                "model_id": "model:override",
            },
        )

    assert response.status_code == 200
    assert response.json()["model_id"] == "model:override"
    mock_model_get.assert_awaited_once_with("model:override")
    assert (
        mock_ainvoke.call_args.kwargs["config"]["configurable"]["model_id"]
        == "model:override"
    )
