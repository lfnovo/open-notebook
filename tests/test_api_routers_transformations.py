"""
Tests for /api/transformations router endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTransformationsRouter:
    """Test suite for /api/transformations endpoints."""

    @pytest.mark.asyncio
    @patch("api.routers.transformations.Transformation")
    async def test_get_transformations(self, mock_transformation_class, client):
        """Test GET /api/transformations returns list."""
        mock_transform = MagicMock()
        mock_transform.id = "transform:1"
        mock_transform.name = "summarize"
        mock_transform.title = "Summarize"
        mock_transform.description = "Creates summary"
        mock_transform.prompt = "Summarize: {content}"
        mock_transform.apply_default = True
        mock_transform.created = "2024-01-01T00:00:00"
        mock_transform.updated = "2024-01-01T00:00:00"

        mock_transformation_class.get_all = AsyncMock(return_value=[mock_transform])

        response = client.get("/api/transformations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "summarize"

    @pytest.mark.asyncio
    @patch("api.routers.transformations.Transformation")
    async def test_create_transformation(self, mock_transformation_class, client):
        """Test POST /api/transformations creates transformation."""
        mock_transform = MagicMock()
        mock_transform.id = "transform:123"
        mock_transform.name = "new_transform"
        mock_transform.title = "New Transform"
        mock_transform.description = "Description"
        mock_transform.prompt = "Prompt: {content}"
        mock_transform.apply_default = False
        mock_transform.created = "2024-01-01T00:00:00"
        mock_transform.updated = "2024-01-01T00:00:00"
        mock_transform.save = AsyncMock()

        mock_transformation_class.return_value = mock_transform

        response = client.post(
            "/api/transformations",
            json={
                "name": "new_transform",
                "title": "New Transform",
                "description": "Description",
                "prompt": "Prompt: {content}",
                "apply_default": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new_transform"

    @pytest.mark.asyncio
    @patch("api.routers.transformations.Transformation")
    async def test_get_transformation_by_id(self, mock_transformation_class, client):
        """Test GET /api/transformations/{id} returns specific transformation."""
        mock_transform = MagicMock()
        mock_transform.id = "transform:123"
        mock_transform.name = "summarize"
        mock_transform.title = "Summarize"
        mock_transform.description = "Description"
        mock_transform.prompt = "Prompt"
        mock_transform.apply_default = True
        mock_transform.created = "2024-01-01T00:00:00"
        mock_transform.updated = "2024-01-01T00:00:00"

        mock_transformation_class.get = AsyncMock(return_value=mock_transform)

        response = client.get("/api/transformations/transform:123")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "summarize"

    @pytest.mark.asyncio
    @patch("api.routers.transformations.Transformation")
    async def test_update_transformation(self, mock_transformation_class, client):
        """Test PUT /api/transformations/{id} updates transformation."""
        mock_transform = MagicMock()
        mock_transform.id = "transform:123"
        mock_transform.name = "updated"
        mock_transform.title = "Updated"
        mock_transform.save = AsyncMock()

        mock_transformation_class.get = AsyncMock(return_value=mock_transform)

        response = client.put(
            "/api/transformations/transform:123",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("api.routers.transformations.Transformation")
    async def test_delete_transformation(self, mock_transformation_class, client):
        """Test DELETE /api/transformations/{id} deletes transformation."""
        mock_transform = MagicMock()
        mock_transform.delete = AsyncMock(return_value=True)

        mock_transformation_class.get = AsyncMock(return_value=mock_transform)

        response = client.delete("/api/transformations/transform:123")
        assert response.status_code == 200
