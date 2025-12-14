import os
import asyncio
from datetime import datetime
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter
from loguru import logger

router = APIRouter()


async def check_tcp_port(host: str, port: int, timeout: float = 3.0) -> bool:
    """Check if a TCP port is open and accepting connections."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return False


async def check_service_health(name: str, url: str, timeout: float = 3.0) -> Dict[str, Any]:
    """Check if a service is responding."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return {
                "name": name,
                "status": "healthy",
                "url": url,
            }
    except httpx.TimeoutException:
        return {
            "name": name,
            "status": "unhealthy",
            "url": url,
            "error": "Connection timeout"
        }
    except httpx.ConnectError:
        return {
            "name": name,
            "status": "unhealthy",
            "url": url,
            "error": "Cannot connect to service"
        }
    except Exception as e:
        return {
            "name": name,
            "status": "unhealthy",
            "url": url,
            "error": str(e)
        }


@router.get("/health/services")
async def get_services_health():
    """Check health of all external services."""
    services = []
    
    # Check SurrealDB
    surreal_url = os.environ.get("SURREAL_URL", "ws://surrealdb:8000")
    # Convert ws:// to http:// for health check
    surreal_http = surreal_url.replace("ws://", "http://").replace("wss://", "https://")
    services.append(await check_service_health("SurrealDB", f"{surreal_http}/health"))
    
    # Check Ollama
    ollama_base = os.environ.get("OLLAMA_API_BASE", "http://ollama:11434")
    services.append(await check_service_health("Ollama", ollama_base))
    
    # Check Whisper
    whisper_url = os.environ.get("WHISPER_API_URL", "http://whisper:9000")
    services.append(await check_service_health("Whisper (Speech-to-Text)", whisper_url))
    
    # Check Piper (uses Wyoming protocol, not HTTP - check TCP port instead)
    piper_host = "piper"
    piper_port = 10200
    piper_healthy = await check_tcp_port(piper_host, piper_port, timeout=3.0)
    services.append({
        "name": "Piper (Text-to-Speech)",
        "status": "healthy" if piper_healthy else "unhealthy",
        "url": f"http://{piper_host}:{piper_port}",
        "error": None if piper_healthy else "Cannot connect to service"
    })
    
    return {
        "services": services,
        "timestamp": datetime.utcnow().isoformat()
    }
