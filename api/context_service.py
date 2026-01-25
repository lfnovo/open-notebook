"""
Context service layer using API.
"""

from typing import Any, Dict, List, Optional, Union

from loguru import logger

from api.client import api_client


class ContextService:
    """Service layer for context operations using API."""

    def __init__(self):
        logger.info("Using API for context operations")

    def get_module_context(
        self, module_id: str, context_config: Optional[Dict] = None
    ) -> Union[Dict[Any, Any], List[Dict[Any, Any]]]:
        """Get context for a module."""
        result = api_client.get_module_context(
            module_id=module_id, context_config=context_config
        )
        return result


# Global service instance
context_service = ContextService()
