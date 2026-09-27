"""Application service: lifecycle guards, settings persistence and HTTP adapter."""
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from open_notebook.modules.registry import ModuleError, Registry


def service_config(item):
    spec = item.service
    if not spec:
        raise ModuleError('This module has no HTTP service', 404)
    base = os.environ.get(spec.url_env, '').rstrip('/')
    key = os.environ.get(spec.key_env, '')
    # Deployment-owned configuration permits adding a local sidecar without
    # recreating the application's container/volumes. Never supplied by HTTP.
    if not base or not key:
        config = Path(os.environ.get('OPEN_NOTEBOOK_SERVICE_CONFIG', 'data/module-services.json'))
        try:
            entry = json.loads(config.read_text()).get(item.id, {}) if config.exists() else {}
            base = base or entry.get('url', '').rstrip('/')
            if not key and entry.get('key_file'):
                key = Path(entry['key_file']).read_text().strip()
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise ModuleError('Module service configuration could not be read.', 503) from exc
    url = urlsplit(base)
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment or not key:
        raise ModuleError('Module service URL and authentication key must be configured.', 503)
    return base, {'Authorization': 'Bearer ' + key}


async def assert_idle(item):
    if not item.service:
        return
    base, headers = service_config(item)
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.get(base+'/'+item.service.health_path, headers=headers)
            response.raise_for_status()
            health = response.json()
            if health.get('status') != 'healthy' or any(health.get(field) for field in item.service.busy_fields):
                raise ModuleError('Module has active work. Wait for completion before disabling.')
            if item.service.pending_path:
                response = await client.get(base+'/'+item.service.pending_path, headers=headers)
                response.raise_for_status()
                runs = response.json()
                if not isinstance(runs, list):
                    raise ModuleError('Could not verify pending jobs; module remains enabled.')
                if any(run.get('status') not in ('completed','paused') for run in runs):
                    raise ModuleError('Pause unfinished research runs before disabling this module.')
    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
        raise ModuleError('Could not verify that the service is idle; module remains enabled.', 503) from exc


class ModuleManager:
    def __init__(self, registry: Registry):
        self.registry = registry

    async def configure(self, module_id, *, enabled=None, settings=None, expected_revision=None):
        async with self.registry.lock(exclusive=True):
            item = self.registry.get(module_id)
            # Existing requests may complete. Only research has an autonomous
            # scheduler, so it must also be paused before its admission closes.
            if enabled is False and module_id in self.registry.enabled():
                await assert_idle(item)
            if enabled is True and item.service:
                service_config(item)
            previous_enabled = module_id in self.registry.enabled()
            previous_settings = self.registry.settings(module_id)
            await asyncio.to_thread(self.registry.update, module_id, enabled=enabled,
                                    settings=settings, expected_revision=expected_revision)
            if enabled is not None and item.service and item.service.control_path:
                try:
                    base, headers = service_config(item)
                    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                        response = await client.post(base+'/'+item.service.control_path, headers=headers, json={'enabled':enabled})
                        response.raise_for_status()
                except (httpx.HTTPError, ModuleError) as exc:
                    await asyncio.to_thread(self.registry.update, module_id, enabled=previous_enabled, settings=previous_settings)
                    raise ModuleError('Service did not apply the module state; the previous configuration was restored.',503) from exc
            return self.registry.catalog()

    async def request(self, module_id, path, method, query, content, request_headers):
        async with self.registry.lock():
            item = self.registry.require_enabled(module_id)
            base, headers = service_config(item)
            if len(content) > 32 * 1024 * 1024:
                raise ModuleError("Module upload is too large", 413)
            for name in ("content-type", "idempotency-key"):
                if request_headers.get(name):
                    headers[name] = request_headers[name]
            # A module declares defaults; explicit per-run choices win. Reports
            # and existing run payloads are never transformed by this adapter.
            bindings = item.request_defaults.get(method + " " + path)
            if bindings:
                try:
                    body = json.loads(content)
                    if not isinstance(body, dict):
                        raise ValueError("Expected object")
                except (ValueError, TypeError) as exc:
                    raise ModuleError("Invalid module request", 422) from exc
                settings = self.registry.settings(module_id)
                for key, setting in bindings.items():
                    body.setdefault(key, settings[setting])
                content = json.dumps(body).encode()
            async with httpx.AsyncClient(timeout=120, follow_redirects=False) as client:
                result = await client.request(method, base + "/" + path, params=query, content=content, headers=headers)
            if 300 <= result.status_code < 400:
                raise ModuleError("Unexpected module service redirect", 502)
            return result
