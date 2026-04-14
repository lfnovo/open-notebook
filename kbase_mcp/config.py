"""
MCP server configuration.

Reads transport and bind settings from environment variables.
"""

import os


MCP_HOST: str = os.environ.get("MCP_HOST", "localhost")
MCP_PORT: int = int(os.environ.get("MCP_PORT", "8080"))
MCP_TRANSPORT: str = os.environ.get("MCP_TRANSPORT", "stdio")  # "stdio" or "sse"
