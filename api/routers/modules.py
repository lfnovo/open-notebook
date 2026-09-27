"""Authenticated module catalog, lifecycle gate and fixed-origin service proxy."""
import asyncio
import re

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from open_notebook.modules.service import ModuleManager

from open_notebook.modules.registry import ModuleError, Registry

router = APIRouter()


def registry() -> Registry:
    try:
        return Registry()
    except Exception as exc:
        # Keep core notebook routes available even if an optional manifest is bad.
        raise HTTPException(503, 'Module configuration could not be loaded.') from exc


@router.get('/modules')
async def list_modules():
    try:
        return await asyncio.to_thread(registry().catalog)
    except ModuleError as exc:
        raise HTTPException(exc.status, str(exc)) from exc


class ModuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool | None = None
    settings: dict | None = None
    expected_revision: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def nonempty(self):
        if self.enabled is None and self.settings is None:
            raise ValueError("No configuration change")
        return self


@router.put('/modules/{module_id}')
async def configure_module(module_id: str, body: ModuleUpdate):
    try:
        return await ModuleManager(registry()).configure(module_id, **body.model_dump())
    except ModuleError as exc:
        raise HTTPException(exc.status, str(exc)) from exc


@router.get('/modules/configuration')
async def export_module_configuration():
    """Portable non-secret policy snapshot for the build and maintenance CLIs."""
    try:
        reg = registry()
        return {**reg.snapshot(), "installed": sorted(reg.installed)}
    except ModuleError as exc:
        raise HTTPException(exc.status, str(exc)) from exc


async def proxy(module_id: str, path: str, request: Request):
    if not re.fullmatch(r'[a-zA-Z0-9_/-]+', path) or '..' in path:
        raise HTTPException(400, 'Invalid module service path')
    try:
        result = await ModuleManager(registry()).request(module_id, path, request.method,
                    request.query_params, await request.body(), request.headers)
        headers = {name: result.headers[name] for name in ('content-type', 'content-disposition', 'cache-control') if name in result.headers}
        return Response(result.content, status_code=result.status_code, headers=headers)
    except ModuleError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(503, 'The local module service could not be reached.') from exc


@router.api_route('/modules/{module_id}/service/{path:path}', methods=['GET','POST'])
async def module_proxy(module_id: str, path: str, request: Request):
    return await proxy(module_id, path, request)


def register_module_routes(app):
    app.include_router(router, prefix='/api', tags=['modules'])
    # Legacy URLs are manifest-owned. No research-specific route in core.
    try:
        items = Registry().manifests.values()
    except Exception:
        return
    for item in items:
        if item.service and item.service.proxy_alias:
            def endpoint(mid):
                async def handler(path: str, request: Request):
                    return await proxy(mid, path, request)
                return handler
            app.add_api_route('/api/'+item.service.proxy_alias+'/{path:path}', endpoint(item.id), methods=['GET','POST'], tags=['modules'])
