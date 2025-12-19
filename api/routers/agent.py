"""
Agent API Router
Provides endpoints for interacting with the research agent.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter()


# Request/Response Models
class AgentExecuteRequest(BaseModel):
    """Request model for agent execution."""
    message: str = Field(..., description="User message or task for the agent")
    thread_id: str = Field(..., description="Thread ID for conversation persistence")
    notebook_id: Optional[str] = Field(None, description="Optional notebook context")
    model_override: Optional[str] = Field(None, description="Optional model override")
    api_key: Optional[str] = Field(None, description="Optional user API key")
    stream: bool = Field(False, description="Whether to stream the response")


class ToolCallInfo(BaseModel):
    """Information about a tool call."""
    tool: str
    input: Dict[str, Any]
    output: Optional[str] = None


class AgentMessage(BaseModel):
    """A message in the agent conversation."""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'tool'")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[ToolCallInfo]] = None


class AgentExecuteResponse(BaseModel):
    """Response model for agent execution."""
    thread_id: str
    messages: List[AgentMessage]
    final_response: Optional[str] = None


class AgentStreamEvent(BaseModel):
    """Event model for streaming responses."""
    type: str = Field(..., description="Event type: 'thinking', 'tool_call', 'tool_result', 'response', 'error'")
    content: Optional[str] = None
    tool: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[str] = None


@router.post("/agent/execute", response_model=AgentExecuteResponse)
async def execute_agent(request: AgentExecuteRequest):
    """
    Execute the research agent with a user message.
    
    The agent will:
    1. Analyze the user's request
    2. Search the knowledge base if needed
    3. Use tools to gather information
    4. Generate a comprehensive response
    """
    try:
        from open_notebook.graphs.agent import run_agent
        
        result = await run_agent(
            message=request.message,
            thread_id=request.thread_id,
            notebook_id=request.notebook_id,
            api_key=request.api_key,
            model_override=request.model_override,
        )
        
        # Convert messages to response format
        messages = []
        final_response = None
        
        for msg in result.get("messages", []):
            if hasattr(msg, "type"):
                role = "user" if msg.type == "human" else "assistant"
            else:
                role = "assistant"
            
            content = msg.content if hasattr(msg, "content") else str(msg)
            
            # Extract tool calls if present
            tool_calls = None
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_calls = [
                    ToolCallInfo(
                        tool=tc.get("name", "unknown"),
                        input=tc.get("args", {}),
                    )
                    for tc in msg.tool_calls
                ]
            
            messages.append(AgentMessage(
                role=role,
                content=content,
                tool_calls=tool_calls,
            ))
            
            # Last assistant message without tool calls is the final response
            if role == "assistant" and not tool_calls:
                final_response = content
        
        return AgentExecuteResponse(
            thread_id=request.thread_id,
            messages=messages,
            final_response=final_response,
        )
    
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.post("/agent/stream")
async def stream_agent(request: AgentExecuteRequest):
    """
    Stream agent execution for real-time UI updates.
    
    Returns Server-Sent Events (SSE) with:
    - thinking: Agent is processing
    - tool_call: Agent is calling a tool
    - tool_result: Tool execution result
    - response: Final agent response
    - error: Error occurred
    """
    async def event_generator():
        try:
            from open_notebook.graphs.agent import stream_agent as agent_stream
            
            async for event in agent_stream(
                message=request.message,
                thread_id=request.thread_id,
                notebook_id=request.notebook_id,
                api_key=request.api_key,
                model_override=request.model_override,
            ):
                # Format as SSE
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
            
            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        except Exception as e:
            logger.error(f"Agent streaming failed: {e}")
            error_event = json.dumps({
                "type": "error",
                "content": str(e)
            })
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/agent/tools")
async def list_agent_tools():
    """
    List all available agent tools.
    
    Returns information about each tool including name, description, and parameters.
    """
    from open_notebook.graphs.agent_tools import AGENT_TOOLS
    
    tools_info = []
    for tool in AGENT_TOOLS:
        tool_info = {
            "name": tool.name,
            "description": tool.description,
        }
        
        # Extract schema if available
        if hasattr(tool, "args_schema") and tool.args_schema:
            schema = tool.args_schema.model_json_schema()
            tool_info["parameters"] = schema.get("properties", {})
            tool_info["required"] = schema.get("required", [])
        
        tools_info.append(tool_info)
    
    return {"tools": tools_info}


@router.get("/agent/models")
async def list_supported_models():
    """
    List supported AI models for the agent.
    
    Currently supports:
    - DeepSeek: deepseek-chat, deepseek-reasoner
    - Qwen (通义千问): qwen-plus, qwen-turbo, qwen-max, qwen-long
    """
    from open_notebook.graphs.agent import SUPPORTED_MODELS
    
    models_list = []
    for model_name, model_info in SUPPORTED_MODELS.items():
        models_list.append({
            "id": model_name,
            "name": model_name,
            "provider": model_info.get("provider"),
            "description": model_info.get("description"),
        })
    
    return {"models": models_list}
