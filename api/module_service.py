"""
Module service layer using API.
"""

from typing import List, Optional

from loguru import logger

from api.client import api_client
from backpack.domain.module import Module


class ModuleService:
    """Service layer for module operations using API."""

    def __init__(self):
        logger.info("Using API for module operations")

    def get_all_modules(self, order_by: str = "updated desc") -> List[Module]:
        """Get all modules."""
        modules_data = api_client.get_modules(order_by=order_by)
        # Convert API response to Module objects
        modules = []
        for mod_data in modules_data:
            mod = Module(
                name=mod_data["name"],
                description=mod_data["description"],
                archived=mod_data["archived"],
            )
            mod.id = mod_data["id"]
            mod.created = mod_data["created"]
            mod.updated = mod_data["updated"]
            modules.append(mod)
        return modules

    def get_module(self, module_id: str) -> Optional[Module]:
        """Get a specific module."""
        response = api_client.get_module(module_id)
        mod_data = response if isinstance(response, dict) else response[0]
        mod = Module(
            name=mod_data["name"],
            description=mod_data["description"],
            archived=mod_data["archived"],
        )
        mod.id = mod_data["id"]
        mod.created = mod_data["created"]
        mod.updated = mod_data["updated"]
        return mod

    def create_module(self, name: str, description: str = "") -> Module:
        """Create a new module."""
        response = api_client.create_module(name, description)
        mod_data = response if isinstance(response, dict) else response[0]
        mod = Module(
            name=mod_data["name"],
            description=mod_data["description"],
            archived=mod_data["archived"],
        )
        mod.id = mod_data["id"]
        mod.created = mod_data["created"]
        mod.updated = mod_data["updated"]
        return mod

    def update_module(self, module: Module) -> Module:
        """Update a module."""
        updates = {
            "name": module.name,
            "description": module.description,
            "archived": module.archived,
        }
        response = api_client.update_module(module.id or "", **updates)
        mod_data = response if isinstance(response, dict) else response[0]
        # Update the module object with the response
        module.name = mod_data["name"]
        module.description = mod_data["description"]
        module.archived = mod_data["archived"]
        module.updated = mod_data["updated"]
        return module

    def delete_module(self, module: Module) -> bool:
        """Delete a module."""
        api_client.delete_module(module.id or "")
        return True


# Global service instance
module_service = ModuleService()
