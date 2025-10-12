from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestSourceChatAPI:
    """Test suite for Source Chat API endpoints."""

    @pytest.fixture
    def sample_source_id(self):
        return "test_source_123"

    @pytest.fixture
    def sample_session_id(self):
        return "test_session_456"

    @patch('api.routers.source_chat.Source.get')
    @patch('api.routers.source_chat.ChatSession.save')
    @patch('api.routers.source_chat.ChatSession.relate')
    def test_create_source_chat_session(self, mock_relate, mock_save, mock_source_get, sample_source_id):
        """Test creating a new source chat session."""
        # Mock source exists
        mock_source = AsyncMock()
        mock_source.id = f"source:{sample_source_id}"
        mock_source_get.return_value = mock_source
        
        # Mock session save and relate
        mock_save.return_value = None
        mock_relate.return_value = None
        
        # Create session request
        request_data = {
            "source_id": sample_source_id,
            "title": "Test Chat Session",
            "model_override": "gpt-4"
        }
        
        response = client.post(
            f"/api/sources/{sample_source_id}/chat/sessions",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Chat Session"
        assert data["source_id"] == sample_source_id
        assert data["model_override"] == "gpt-4"
        assert "id" in data
        assert "created" in data

    @patch('api.routers.source_chat.Source.get')
    def test_create_session_source_not_found(self, mock_source_get, sample_source_id):
        """Test creating session for non-existent source."""
        mock_source_get.return_value = None
        
        request_data = {
            "source_id": sample_source_id,
            "title": "Test Chat Session"
        }
        
        response = client.post(
            f"/api/sources/{sample_source_id}/chat/sessions",
            json=request_data
        )
        
        assert response.status_code == 404
        assert "Source not found" in response.json()["detail"]

    @patch('api.routers.source_chat.Source.get')
    @patch('api.routers.source_chat.repo_query')
    def test_get_source_chat_sessions(self, mock_repo_query, mock_source_get, sample_source_id):
        """Test getting all chat sessions for a source."""
        # Mock source exists
        mock_source = AsyncMock()
        mock_source.id = f"source:{sample_source_id}"
        mock_source_get.return_value = mock_source
        
        # Mock query returns sessions
        mock_repo_query.return_value = [
            {"in": "chat_session:session1"},
            {"in": "chat_session:session2"}
        ]
        
        # Mock ChatSession.get for each session
        with patch('api.routers.source_chat.ChatSession.get') as mock_session_get:
            mock_session1 = AsyncMock()
            mock_session1.id = "chat_session:session1"
            mock_session1.title = "Session 1"
            mock_session1.created = "2024-01-01T00:00:00Z"
            mock_session1.updated = "2024-01-01T00:00:00Z"
            mock_session1.model_override = None
            
            mock_session2 = AsyncMock()
            mock_session2.id = "chat_session:session2"
            mock_session2.title = "Session 2"
            mock_session2.created = "2024-01-01T00:00:00Z"
            mock_session2.updated = "2024-01-01T00:00:00Z"
            mock_session2.model_override = "gpt-4"
            
            mock_session_get.side_effect = [mock_session1, mock_session2]
            
            response = client.get(f"/api/sources/{sample_source_id}/chat/sessions")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["title"] == "Session 1"
            assert data[1]["title"] == "Session 2"
            assert data[1]["model_override"] == "gpt-4"

    @patch('api.routers.source_chat.Source.get')
    @patch('api.routers.source_chat.ChatSession.get')
    @patch('api.routers.source_chat.repo_query')
    @patch('api.routers.source_chat.source_chat_graph.get_state')
    def test_get_source_chat_session_with_messages(
        self, mock_get_state, mock_repo_query, mock_session_get, mock_source_get, 
        sample_source_id, sample_session_id
    ):
        """Test getting a specific chat session with messages."""
        # Mock source exists
        mock_source = AsyncMock()
        mock_source.id = f"source:{sample_source_id}"
        mock_source_get.return_value = mock_source
        
        # Mock session exists
        mock_session = AsyncMock()
        mock_session.id = f"chat_session:{sample_session_id}"
        mock_session.title = "Test Session"
        mock_session.created = "2024-01-01T00:00:00Z"
        mock_session.updated = "2024-01-01T00:00:00Z"
        mock_session.model_override = "gpt-4"
        mock_session_get.return_value = mock_session
        
        # Mock relation exists
        mock_repo_query.return_value = [{"relation": "exists"}]
        
        # Mock graph state with messages
        mock_message = AsyncMock()
        mock_message.type = "human"
        mock_message.content = "Hello"
        mock_message.id = "msg_1"
        
        mock_state = AsyncMock()
        mock_state.values = {
            "messages": [mock_message],
            "context_indicators": {"sources": ["source:123"], "insights": ["insight:456"], "notes": []}
        }
        mock_get_state.return_value = mock_state
        
        response = client.get(f"/api/sources/{sample_source_id}/chat/sessions/{sample_session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Session"
        assert data["model_override"] == "gpt-4"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hello"
        assert data["context_indicators"]["sources"] == ["source:123"]

    @patch('api.routers.source_chat.Source.get')
    @patch('api.routers.source_chat.ChatSession.get')
    @patch('api.routers.source_chat.repo_query')
    @patch('api.routers.source_chat.ChatSession.save')
    def test_update_source_chat_session(
        self, mock_save, mock_repo_query, mock_session_get, mock_source_get,
        sample_source_id, sample_session_id
    ):
        """Test updating a source chat session."""
        # Mock source exists
        mock_source = AsyncMock()
        mock_source.id = f"source:{sample_source_id}"
        mock_source_get.return_value = mock_source
        
        # Mock session exists
        mock_session = AsyncMock()
        mock_session.id = f"chat_session:{sample_session_id}"
        mock_session.title = "Old Title"
        mock_session.created = "2024-01-01T00:00:00Z"
        mock_session.updated = "2024-01-01T00:00:00Z"
        mock_session.model_override = None
        mock_session_get.return_value = mock_session
        
        # Mock relation exists
        mock_repo_query.return_value = [{"relation": "exists"}]
        
        # Mock save
        mock_save.return_value = None
        
        request_data = {
            "title": "New Title",
            "model_override": "gpt-4"
        }
        
        response = client.put(
            f"/api/sources/{sample_source_id}/chat/sessions/{sample_session_id}",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        # Note: The mock will still return the original values unless we update them
        # In a real test, we'd want to verify the session was updated properly

    def test_api_endpoints_structure(self):
        """Test that all expected endpoints are properly structured."""
        # Test endpoint paths are correctly formed
        from api.routers.source_chat import router

        routes = [route.path for route in router.routes]  # type: ignore[attr-defined]
        expected_routes = [
            "/sources/{source_id}/chat/sessions",
            "/sources/{source_id}/chat/sessions/{session_id}",
            "/sources/{source_id}/chat/sessions/{session_id}/messages"
        ]
        
        for expected_route in expected_routes:
            assert any(expected_route in route for route in routes), f"Route {expected_route} not found"