from importlib import import_module
from typing import Any, Dict, Optional

from loguru import logger
from surreal_commands import get_command_status, submit_command

COMMAND_MODULES = (
    "commands.embedding_commands",
    "commands.example_commands",
    "commands.external_api_commands",
    "commands.kg_commands",
    "commands.podcast_commands",
    "commands.source_commands",
)


def ensure_command_modules_registered() -> None:
    for module_name in COMMAND_MODULES:
        import_module(module_name)


async def submit_command_job(
    module_name: str,
    command_name: str,
    command_args: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    *,
    ensure_registered: bool = True,
) -> str:
    if ensure_registered:
        ensure_command_modules_registered()

    cmd_id = submit_command(module_name, command_name, command_args)
    if not cmd_id:
        raise ValueError("Failed to get cmd_id from submit_command")

    cmd_id_str = str(cmd_id)
    logger.info(f"Submitted command job: {cmd_id_str} for {module_name}.{command_name}")
    return cmd_id_str


async def command_status_payload(job_id: str) -> Dict[str, Any]:
    status = await get_command_status(job_id)
    return {
        "job_id": job_id,
        "command_id": job_id,
        "status": status.status if status else "unknown",
        "result": status.result if status else None,
        "error_message": getattr(status, "error_message", None) if status else None,
        "created": str(status.created)
        if status and hasattr(status, "created") and status.created
        else None,
        "updated": str(status.updated)
        if status and hasattr(status, "updated") and status.updated
        else None,
        "progress": getattr(status, "progress", None) if status else None,
    }
