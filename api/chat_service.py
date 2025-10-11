"""
Chat service for API operations.
Provides async interface for chat functionality.
"""
import os
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


class ChatService:
    """Service for chat-related API operations"""
    
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:5055")
        # Add authentication header if password is set
        self.headers = {}
        password = os.getenv("OPEN_NOTEBOOK_PASSWORD")
        if password:
            self.headers["Authorization"] = f"Bearer {password}"
    
    async def get_sessions(self, notebook_id: str) -> List[Dict[str, Any]]:
        """Get all chat sessions for a notebook"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/chat/sessions",
                    params={"notebook_id": notebook_id},
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching chat sessions: {str(e)}")
            raise
    
    async def create_session(
        self,
        notebook_id: str,
        title: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new chat session"""
        try:
            data: Dict[str, Any] = {"notebook_id": notebook_id}
            if title is not None:
                data["title"] = title
            if model_override is not None:
                data["model_override"] = model_override
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat/sessions",
                    json=data,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error creating chat session: {str(e)}")
            raise
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get a specific session with messages"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/chat/sessions/{session_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching session: {str(e)}")
            raise
    
    async def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update session properties"""
        try:
            data: Dict[str, Any] = {}
            if title is not None:
                data["title"] = title
            if model_override is not None:
                data["model_override"] = model_override

            if not data:
                raise ValueError("At least one field must be provided to update a session")

            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/api/chat/sessions/{session_id}",
                    json=data,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise
    
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a chat session"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/api/chat/sessions/{session_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            raise
    
    async def execute_chat(
        self,
        session_id: str,
        message: str,
        context: Dict[str, Any],
        model_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a chat request"""
        try:
            data = {
                "session_id": session_id,
                "message": message, 
                "context": context
            }
            if model_override is not None:
                data["model_override"] = model_override
            
            async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for chat
                response = await client.post(
                    f"{self.base_url}/api/chat/execute",
                    json=data,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error executing chat: {str(e)}")
            raise
    
    async def build_context(self, notebook_id: str, context_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build context for a notebook"""
        try:
            data = {
                "notebook_id": notebook_id,
                "context_config": context_config
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat/context",
                    json=data,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error building context: {str(e)}")
            raise


# Global instance
chat_service = ChatService()
