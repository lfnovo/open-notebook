"""
Tests for /api/commands router and CommandService.

Covers command job submission and status tracking.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCommandsRouter:
    """Test suite for /api/commands endpoints."""

    @pytest.mark.asyncio
    @patch("api.routers.commands.CommandService")
    async def test_submit_command_job(self, mock_service, client):
        """Test POST /api/commands/jobs submits command."""
        mock_service.submit_command_job = AsyncMock(return_value="job:123")

        response = client.post(
            "/api/commands/jobs",
            json={
                "command": "process_text",
                "app": "open_notebook",
                "input": {"text": "Hello", "operation": "uppercase"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job:123"
        assert data["status"] == "submitted"

    @pytest.mark.asyncio
    @patch("api.routers.commands.CommandService")
    async def test_submit_command_job_error(self, mock_service, client):
        """Test POST /api/commands/jobs handles errors."""
        mock_service.submit_command_job = AsyncMock(side_effect=Exception("Command failed"))

        response = client.post(
            "/api/commands/jobs",
            json={
                "command": "invalid",
                "app": "open_notebook",
                "input": {},
            },
        )
        assert response.status_code == 500

    @pytest.mark.asyncio
    @patch("api.routers.commands.CommandService")
    async def test_get_command_status(self, mock_service, client):
        """Test GET /api/commands/jobs/{id} returns job status."""
        mock_status = {
            "job_id": "job:123",
            "status": "completed",
            "result": {"output": "HELLO"},
            "created": "2024-01-01T00:00:00",
            "updated": "2024-01-01T00:00:00",
        }
        mock_service.get_command_status = AsyncMock(return_value=mock_status)

        response = client.get("/api/commands/jobs/job:123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] == {"output": "HELLO"}

    @pytest.mark.asyncio
    @patch("api.routers.commands.CommandService")
    async def test_list_command_jobs(self, mock_service, client):
        """Test GET /api/commands/jobs returns job list."""
        mock_jobs = [
            {"job_id": "job:1", "status": "completed"},
            {"job_id": "job:2", "status": "running"},
        ]
        mock_service.list_command_jobs = AsyncMock(return_value=mock_jobs)

        response = client.get("/api/commands/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    @patch("api.routers.commands.CommandService")
    async def test_list_command_jobs_with_filters(self, mock_service, client):
        """Test GET /api/commands/jobs with filters."""
        mock_service.list_command_jobs = AsyncMock(return_value=[])

        response = client.get(
            "/api/commands/jobs?command_filter=process_text&status_filter=completed&limit=10"
        )
        assert response.status_code == 200
        mock_service.list_command_jobs.assert_called_once_with(
            command_filter="process_text", status_filter="completed", limit=10
        )


class TestCommandService:
    """Test suite for CommandService."""

    @pytest.mark.asyncio
    @patch("api.command_service.submit_command")
    async def test_submit_command_job_success(self, mock_submit_command):
        """Test CommandService.submit_command_job submits successfully."""
        from api.command_service import CommandService

        mock_submit_command.return_value = "cmd:123"

        job_id = await CommandService.submit_command_job(
            module_name="open_notebook",
            command_name="process_text",
            command_args={"text": "Hello"},
        )
        assert job_id == "cmd:123"

    @pytest.mark.asyncio
    @patch("api.command_service.submit_command")
    @patch("builtins.__import__")
    async def test_submit_command_job_import_error(self, mock_import, mock_submit_command):
        """Test CommandService.submit_command_job handles import errors."""
        from api.command_service import CommandService

        # Mock import failure for commands.podcast_commands
        original_import = __import__
        def failing_import(name, *args, **kwargs):
            if name == "commands.podcast_commands":
                raise ImportError("Module not found")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            with pytest.raises(ValueError, match="Command modules not available"):
                await CommandService.submit_command_job(
                    module_name="open_notebook",
                    command_name="process_text",
                    command_args={},
                )

    @pytest.mark.asyncio
    @patch("api.command_service.get_command_status")
    async def test_get_command_status_success(self, mock_get_status):
        """Test CommandService.get_command_status returns status."""
        from api.command_service import CommandService

        mock_status = MagicMock()
        mock_status.status = "completed"
        mock_status.result = {"output": "result"}
        mock_status.created = "2024-01-01T00:00:00"
        mock_status.updated = "2024-01-01T00:00:00"
        mock_status.error_message = None
        mock_status.progress = None

        mock_get_status.return_value = mock_status

        status = await CommandService.get_command_status("job:123")
        assert status["status"] == "completed"
        assert status["result"] == {"output": "result"}

    @pytest.mark.asyncio
    @patch("api.command_service.get_command_status")
    async def test_get_command_status_none(self, mock_get_status):
        """Test CommandService.get_command_status handles None status."""
        from api.command_service import CommandService

        mock_get_status.return_value = None

        status = await CommandService.get_command_status("job:999")
        assert status["status"] == "unknown"
        assert status["result"] is None

    @pytest.mark.asyncio
    async def test_list_command_jobs(self):
        """Test CommandService.list_command_jobs returns empty list."""
        from api.command_service import CommandService

        jobs = await CommandService.list_command_jobs()
        assert jobs == []

    @pytest.mark.asyncio
    async def test_cancel_command_job(self):
        """Test CommandService.cancel_command_job logs attempt."""
        from api.command_service import CommandService

        result = await CommandService.cancel_command_job("job:123")
        assert result is True
