from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from surreal_commands import registry

from api.command_service import CommandService

router = APIRouter()

class CommandExecutionRequest(BaseModel):
    command: str = Field(..., description="Command function name (e.g., 'process_text')")
    app: str = Field(..., description="Application name (e.g., 'open_notebook')")
    input: Dict[str, Any] = Field(..., description="Arguments to pass to the command")

class CommandJobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class CommandJobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None

@router.post("/commands/jobs", response_model=CommandJobResponse)
async def execute_command(request: CommandExecutionRequest):
    """
    Submit a command for background processing.
    Returns immediately with job ID for status tracking.
    
    Example request:
    {
        "command": "process_text",
        "app": "open_notebook", 
        "input": { 
            "text": "Hello world", 
            "operation": "uppercase" 
        }
    }
    """
    try:
        # Submit command using app name (not module name)
        job_id = await CommandService.submit_command_job(
            module_name=request.app,  # This should be "open_notebook"
            command_name=request.command,
            command_args=request.input
        )
        
        return CommandJobResponse(
            job_id=job_id,
            status="submitted",
            message=f"Command '{request.command}' submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting command: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit command: {str(e)}"
        )

@router.get("/commands/jobs/{job_id}", response_model=CommandJobStatusResponse)
async def get_command_job_status(job_id: str):
    """Get the status of a specific command job"""
    try:
        status_data = await CommandService.get_command_status(job_id)
        return CommandJobStatusResponse(**status_data)
        
    except Exception as e:
        logger.error(f"Error fetching job status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch job status: {str(e)}"
        )

@router.get("/commands/jobs", response_model=List[Dict[str, Any]])
async def list_command_jobs(
    command_filter: Optional[str] = Query(None, description="Filter by command name"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of jobs to return")
):
    """List command jobs with optional filtering"""
    try:
        jobs = await CommandService.list_command_jobs(
            command_filter=command_filter,
            status_filter=status_filter,
            limit=limit
        )
        return jobs
        
    except Exception as e:
        logger.error(f"Error listing command jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list command jobs: {str(e)}"
        )

@router.delete("/commands/jobs/{job_id}")
async def cancel_command_job(job_id: str):
    """Cancel a running command job"""
    try:
        success = await CommandService.cancel_command_job(job_id)
        return {"job_id": job_id, "cancelled": success}
        
    except Exception as e:
        logger.error(f"Error cancelling command job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel command job: {str(e)}"
        )

@router.get("/commands/embedding/status")
async def get_embedding_tasks_status():
    """Get status of all embedding-related tasks"""
    try:
        from open_notebook.database.repository import repo_query
        from datetime import datetime, timedelta
        
        # Query only active/recent embedding-related commands
        # Limit to last 2 hours to keep it fast
        recent_cutoff = datetime.utcnow() - timedelta(hours=2)
        
        # Optimized query - only get running/pending tasks first
        query_active = """
            SELECT * FROM command
            WHERE command IN ['embed_chunk', 'embed_single_item', 'vectorize_source', 'rebuild_embeddings']
            AND status IN ['running', 'pending']
            ORDER BY created DESC
            LIMIT 50
        """
        
        # Get recently completed/failed (last 2 hours, limit 20)
        query_recent = """
            SELECT * FROM command
            WHERE command IN ['embed_chunk', 'embed_single_item', 'vectorize_source', 'rebuild_embeddings']
            AND status IN ['completed', 'failed']
            AND created > $cutoff
            ORDER BY created DESC
            LIMIT 20
        """
        
        # Run queries in parallel for speed
        import asyncio
        active_results, recent_results = await asyncio.gather(
            repo_query(query_active, {}),
            repo_query(query_recent, {"cutoff": recent_cutoff.isoformat()}),
            return_exceptions=True
        )
        
        # Handle query errors gracefully
        if isinstance(active_results, Exception):
            logger.error(f"Error fetching active tasks: {active_results}")
            active_results = []
        if isinstance(recent_results, Exception):
            logger.error(f"Error fetching recent tasks: {recent_results}")
            recent_results = []
        
        # Combine results
        all_results = list(active_results) + list(recent_results)
        
        tasks = []
        summary = {
            "total": len(all_results),
            "running": 0,
            "pending": 0,
            "completed_recently": 0,
            "failed_recently": 0
        }
        
        for row in all_results:
            status = row.get("status", "unknown")
            task = {
                "job_id": str(row.get("id", "")),
                "command": row.get("command", "unknown"),
                "status": status,
                "created": row.get("created"),
                "updated": row.get("updated"),
                "error_message": row.get("error_message"),
                "progress": row.get("progress"),
            }
            
            # Try to extract source info from input
            input_data = row.get("input", {})
            if isinstance(input_data, dict):
                task["source_id"] = input_data.get("source_id")
            
            tasks.append(task)
            
            # Update summary
            if status == "running":
                summary["running"] += 1
            elif status == "pending":
                summary["pending"] += 1
            elif status == "completed":
                summary["completed_recently"] += 1
            elif status == "failed":
                summary["failed_recently"] += 1
        
        return {
            "tasks": tasks,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error fetching embedding tasks: {e}")
        # Return empty state instead of failing
        return {
            "tasks": [],
            "summary": {
                "total": 0,
                "running": 0,
                "pending": 0,
                "completed_recently": 0,
                "failed_recently": 0
            }
        }

@router.get("/commands/registry/debug")
async def debug_registry():
    """Debug endpoint to see what commands are registered"""
    try:
        # Get all registered commands
        all_items = registry.get_all_commands()
        
        # Create JSON-serializable data
        command_items = []
        for item in all_items:
            try:
                command_items.append({
                    "app_id": item.app_id,
                    "name": item.name,
                    "full_id": f"{item.app_id}.{item.name}"
                })
            except Exception as item_error:
                logger.error(f"Error processing item: {item_error}")
        
        # Get the basic command structure
        try:
            commands_dict: dict[str, list[str]] = {}
            for item in all_items:
                if item.app_id not in commands_dict:
                    commands_dict[item.app_id] = []
                commands_dict[item.app_id].append(item.name)
        except Exception:
            commands_dict = {}
        
        return {
            "total_commands": len(all_items),
            "commands_by_app": commands_dict,
            "command_items": command_items
        }
        
    except Exception as e:
        logger.error(f"Error debugging registry: {str(e)}")
        return {
            "error": str(e),
            "total_commands": 0,
            "commands_by_app": {},
            "command_items": []
        }