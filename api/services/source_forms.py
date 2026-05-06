import json
from typing import Optional

from fastapi import File, Form, UploadFile
from loguru import logger

from api.models import SourceCreate


def str_to_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes", "on")


def parse_source_form_data(
    type: str = Form(...),
    workspace_id: Optional[str] = Form(None),
    notebook_id: Optional[str] = Form(None),
    notebooks: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    file_path: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    transformations: Optional[str] = Form(None),
    embed: str = Form("false"),
    delete_source: str = Form("false"),
    async_processing: str = Form("false"),
    visibility: str = Form("private"),
    file: Optional[UploadFile] = File(None),
) -> tuple[SourceCreate, Optional[UploadFile]]:
    """Parse source form data into a SourceCreate model plus upload file."""
    if not isinstance(file_path, str):
        file_path = None

    embed_bool = str_to_bool(embed)
    delete_source_bool = str_to_bool(delete_source)
    async_processing_bool = str_to_bool(async_processing)

    notebooks_list = None
    if notebooks:
        try:
            notebooks_list = json.loads(notebooks)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in notebooks field: {notebooks}")
            raise ValueError("Invalid JSON in notebooks field")

    transformations_list = []
    if transformations:
        try:
            transformations_list = json.loads(transformations)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in transformations field: {transformations}")
            raise ValueError("Invalid JSON in transformations field")

    try:
        source_data = SourceCreate(
            type=type,
            workspace_id=workspace_id,
            notebook_id=notebook_id,
            notebooks=notebooks_list,
            url=url,
            content=content,
            title=title,
            file_path=file_path,
            transformations=transformations_list,
            embed=embed_bool,
            delete_source=delete_source_bool,
            async_processing=async_processing_bool,
            visibility=visibility,
        )
    except Exception as e:
        logger.error(f"Failed to create SourceCreate instance: {e}")
        raise

    return source_data, file
