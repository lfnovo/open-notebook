# """
# Chat service for API operations.
# Provides async interface for chat functionality.
# """

# import os
# from typing import Any, Dict, List, Optional

# import httpx
# from loguru import logger


# class ChatService:
#     """Service for chat-related API operations"""

#     def __init__(self):
#         self.base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:5055")
#         # Add authentication header if password is set
#         self.headers = {}
#         password = os.getenv("OPEN_NOTEBOOK_PASSWORD")
#         if password:
#             self.headers["Authorization"] = f"Bearer {password}"

#     async def get_sessions(self, notebook_id: str) -> List[Dict[str, Any]]:
#         """Get all chat sessions for a notebook"""
#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.get(
#                     f"{self.base_url}/api/chat/sessions",
#                     params={"notebook_id": notebook_id},
#                     headers=self.headers,
#                 )
#                 response.raise_for_status()
#                 return response.json()
#         except Exception as e:
#             logger.error(f"Error fetching chat sessions: {str(e)}")
#             raise

#     async def create_session(
#         self,
#         notebook_id: str,
#         title: Optional[str] = None,
#         model_override: Optional[str] = None,
#     ) -> Dict[str, Any]:
#         """Create a new chat session"""
#         try:
#             data: Dict[str, Any] = {"notebook_id": notebook_id}
#             if title is not None:
#                 data["title"] = title
#             if model_override is not None:
#                 data["model_override"] = model_override

#             async with httpx.AsyncClient() as client:
#                 response = await client.post(
#                     f"{self.base_url}/api/chat/sessions",
#                     json=data,
#                     headers=self.headers,
#                 )
#                 response.raise_for_status()
#                 return response.json()
#         except Exception as e:
#             logger.error(f"Error creating chat session: {str(e)}")
#             raise

#     async def get_session(self, session_id: str) -> Dict[str, Any]:
#         """Get a specific session with messages"""
#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.get(
#                     f"{self.base_url}/api/chat/sessions/{session_id}",
#                     headers=self.headers,
#                 )
#                 response.raise_for_status()
#                 return response.json()
#         except Exception as e:
#             logger.error(f"Error fetching session: {str(e)}")
#             raise

#     async def update_session(
#         self,
#         session_id: str,
#         title: Optional[str] = None,
#         model_override: Optional[str] = None,
#     ) -> Dict[str, Any]:
#         """Update session properties"""
#         try:
#             data: Dict[str, Any] = {}
#             if title is not None:
#                 data["title"] = title
#             if model_override is not None:
#                 data["model_override"] = model_override

#             if not data:
#                 raise ValueError(
#                     "At least one field must be provided to update a session"
#                 )

#             async with httpx.AsyncClient() as client:
#                 response = await client.put(
#                     f"{self.base_url}/api/chat/sessions/{session_id}",
#                     json=data,
#                     headers=self.headers,
#                 )
#                 response.raise_for_status()
#                 return response.json()
#         except Exception as e:
#             logger.error(f"Error updating session: {str(e)}")
#             raise

#     async def delete_session(self, session_id: str) -> Dict[str, Any]:
#         """Delete a chat session"""
#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.delete(
#                     f"{self.base_url}/api/chat/sessions/{session_id}",
#                     headers=self.headers,
#                 )
#                 response.raise_for_status()
#                 return response.json()
#         except Exception as e:
#             logger.error(f"Error deleting session: {str(e)}")
#             raise

#     async def execute_chat(
#         self,
#         session_id: str,
#         message: str,
#         context: Dict[str, Any],
#         model_override: Optional[str] = None,
#     ) -> Dict[str, Any]:
#         """Execute a chat request"""
#         try:
#             data = {"session_id": session_id, "message": message, "context": context}
#             if model_override is not None:
#                 data["model_override"] = model_override

#             # Short connect timeout (10s), long read timeout (10 min) for Ollama/local LLMs
#             timeout = httpx.Timeout(connect=10.0, read=600.0, write=30.0, pool=10.0)
#             async with httpx.AsyncClient(timeout=timeout) as client:
#                 response = await client.post(
#                     f"{self.base_url}/api/chat/execute", json=data, headers=self.headers
#                 )
#                 response.raise_for_status()
#                 return response.json()
#         except Exception as e:
#             logger.error(f"Error executing chat: {str(e)}")
#             raise

#     async def build_context(
#         self, notebook_id: str, context_config: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """Build context for a notebook"""
#         try:
#             data = {"notebook_id": notebook_id, "context_config": context_config}

#             async with httpx.AsyncClient() as client:
#                 response = await client.post(
#                     f"{self.base_url}/api/chat/context", json=data, headers=self.headers
#                 )
#                 response.raise_for_status()
#                 return response.json()
#         except Exception as e:
#             logger.error(f"Error building context: {str(e)}")
#             raise


# # Global instance
# chat_service = ChatService()





"""
Chat service for API operations.
Provides async interface for chat functionality.
"""

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

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
                    headers=self.headers,
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
                    headers=self.headers,
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
                    headers=self.headers,
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
                raise ValueError(
                    "At least one field must be provided to update a session"
                )

            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/api/chat/sessions/{session_id}",
                    json=data,
                    headers=self.headers,
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
                    headers=self.headers,
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
        """Execute a chat request (non-streaming)"""
        try:
            data = {"session_id": session_id, "message": message, "context": context}
            if model_override is not None:
                data["model_override"] = model_override

            # Short connect timeout (10s), long read timeout (10 min) for Ollama/local LLMs
            timeout = httpx.Timeout(connect=10.0, read=600.0, write=30.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat/execute", json=data, headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error executing chat: {str(e)}")
            raise

    async def stream_chat(
        self,
        session_id: str,
        message: str,
        context: Dict[str, Any],
        model_override: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        ✅ નવી method: Streaming chat — tokens real-time yield કરે છે.

        Usage:
            async for event in chat_service.stream_chat(...):
                if 'token' in event:
                    # live token
                    print(event['token'], end='', flush=True)
                elif event.get('done'):
                    # streaming complete
                    break
                elif 'error' in event:
                    # error occurred
                    raise Exception(event['error'])
        """
        data: Dict[str, Any] = {
            "session_id": session_id,
            "message": message,
            "context": context,
        }
        if model_override is not None:
            data["model_override"] = model_override

        # Long timeout for streaming — local LLMs slow હોઈ શકે
        timeout = httpx.Timeout(connect=10.0, read=600.0, write=30.0, pool=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat/stream-execute",
                    json=data,
                    headers={**self.headers, "Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()

                    # SSE lines parse કરો
                    async for line in response.aiter_lines():
                        line = line.strip()

                        # SSE format: "data: {...json...}"
                        if not line.startswith("data:"):
                            continue

                        raw = line[len("data:"):].strip()
                        if not raw:
                            continue

                        try:
                            event = json.loads(raw)
                            yield event

                            # Done signal આવે તો stop
                            if event.get("done"):
                                break

                        except json.JSONDecodeError:
                            logger.warning(f"Invalid SSE JSON: {raw!r}")
                            continue

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in stream_chat: {e.response.status_code} {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in stream_chat: {str(e)}")
            raise

    async def build_context(
        self, notebook_id: str, context_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build context for a notebook"""
        try:
            data = {"notebook_id": notebook_id, "context_config": context_config}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat/context", json=data, headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error building context: {str(e)}")
            raise


# Global instance
chat_service = ChatService()