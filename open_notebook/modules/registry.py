"""Validated manifests and atomic configuration for bundled modules.

Only trusted source manifests are loaded. They describe UI and fixed-origin HTTP
services; a manifest cannot inject Python imports or install dependencies.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from open_notebook.exceptions import ConfigurationError
from open_notebook.modules.contracts import SettingSpec, ModelPolicySpec

ID = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"


class ModuleError(ConfigurationError):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


class FrontendSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry: str = Field(pattern=r"^[a-zA-Z0-9_/-]+\.tsx$")
    route: str = Field(pattern=r"^/[a-z][a-z0-9/-]*$")
    label_key: str
    section: Literal["collect", "process", "create", "manage"] = "process"
    icon: Literal["telescope", "puzzle"] = "puzzle"
    search_widget: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_/-]+\.tsx$")


class ServiceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    key_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    health_path: str = Field(default="health", pattern=r"^[a-zA-Z0-9_/-]+$")
    busy_fields: list[str] = []
    pending_path: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_/-]+$")
    proxy_alias: str | None = Field(default=None, pattern=ID)
    control_path: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_/-]+$")


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    id: str = Field(pattern=ID)
    name: str
    description: str
    version: str
    author: str
    activation: Literal["runtime", "external", "build"]
    dependencies: list[str] = []
    frontend: FrontendSpec | None = None
    service: ServiceSpec | None = None
    settings: list[SettingSpec] = Field(default_factory=list)
    model_policies: list[ModelPolicySpec] = Field(default_factory=list)
    request_defaults: dict[str, dict[str, str]] = Field(default_factory=dict)


class Registry:
    def __init__(self, root: Path | None = None, state: Path | None = None):
        self.root = root or Path(os.environ.get("OPEN_NOTEBOOK_MODULE_DIR", "modules"))
        self.state = state or Path(os.environ.get("OPEN_NOTEBOOK_MODULE_STATE", "data/modules.json"))
        self.manifests: dict[str, Manifest] = {}
        for path in sorted(self.root.glob("*/module.json")):
            item = Manifest.model_validate_json(path.read_text())
            if item.id != path.parent.name or item.id in self.manifests:
                raise ModuleError("Module ID must match its unique directory", 503)
            self.manifests[item.id] = item
        self._validate_graph()
        for item in self.manifests.values():
            keys = [field.key for field in item.settings]
            if len(keys) != len(set(keys)):
                raise ModuleError("Duplicate setting key", 503)
            references = [key for policy in item.model_policies for key in policy.config.values()]
            references += [key for route in item.request_defaults.values() for key in route.values()]
            if not set(references) <= set(keys):
                raise ModuleError("Unknown setting in module contract", 503)
        build_file = self.root / "build.json"
        self.applied_settings = json.loads(build_file.read_text()).get("settings", {}) if build_file.exists() else {}
        install_file = self.root / "installed.json"
        installed = json.loads(install_file.read_text()) if install_file.exists() else []
        if not isinstance(installed, list) or any(not isinstance(x, str) or x not in self.manifests for x in installed):
            raise ModuleError("Invalid installed module inventory", 503)
        self.installed = set(installed)
        for mid in self.installed:
            if not set(self.manifests[mid].dependencies) <= self.installed:
                raise ModuleError("Installed module dependency missing", 503)

    def _validate_graph(self):
        seen, visiting, aliases, routes = set(), set(), set(), set()
        def visit(mid):
            if mid in visiting or mid not in self.manifests:
                raise ModuleError("Module dependency cycle or unknown dependency", 503)
            if mid in seen:
                return
            visiting.add(mid)
            for dep in self.manifests[mid].dependencies:
                visit(dep)
            visiting.remove(mid)
            seen.add(mid)
        for item in self.manifests.values():
            visit(item.id)
            if item.frontend:
                route = item.frontend.route
                if route in routes or route.split('/')[1] in {'api','settings','sources','notebooks','search','podcasts','login','modules','advanced','transformations'}:
                    raise ModuleError("Module UI route collision", 503)
                routes.add(route)
            if item.service and item.service.proxy_alias:
                alias = item.service.proxy_alias
                if alias in aliases or alias in {'modules','auth','config','models','notebooks','sources','notes','chat','settings','search','podcasts','providers','credentials','commands','embedding','transformations','insights','languages','capabilities','episode-profiles','speaker-profiles'}:
                    raise ModuleError("Module API alias collision", 503)
                aliases.add(alias)

    def snapshot(self) -> dict:
        """Read-through repository: API and workers see the same atomic revision.

        v1 migrations preserve the previous runtime choice and installed external
        modules. Fresh installations enable only modules explicitly bundled.
        """
        try:
            source = self.state if self.state.exists() else self.root / "defaults.json"
            if source.exists():
                data = json.loads(source.read_text())
                if data.get("version") == 1:
                    data = {"version": 2, "revision": 0, "enabled": sorted(set(data["enabled"]) | {
                        mid for mid in self.installed if self.manifests[mid].activation != "runtime"
                    }), "settings": {}}
            else:
                explicit = os.environ.get("OPEN_NOTEBOOK_MODULES")
                ids = set(self.installed) if explicit is None else {
                    x.strip() for x in explicit.split(",") if x.strip()
                } | {mid for mid in self.installed if self.manifests[mid].activation != "runtime"}
                data = {"version": 2, "revision": 0, "enabled": sorted(ids), "settings": {}}
            if data.get("version") != 2 or type(data.get("revision")) is not int or data["revision"] < 0:
                raise ValueError("Invalid version or revision")
            ids = data["enabled"]
            if not isinstance(ids, list) or any(not isinstance(x, str) or x not in self.manifests for x in ids):
                raise ValueError("Unknown module")
            for mid in ids:
                if mid not in self.installed and self.manifests[mid].activation != "build":
                    raise ValueError("Uninstalled module")
                if not set(self.manifests[mid].dependencies) <= set(ids):
                    raise ValueError("Disabled dependency")
            settings = data["settings"]
            if not isinstance(settings, dict) or set(settings) - self.manifests.keys():
                raise ValueError("Unknown settings owner")
            for mid, values in settings.items():
                self.validate_settings(mid, values)
            revisions = data.setdefault("module_revisions", {})
            if not isinstance(revisions, dict) or any(mid not in self.manifests or type(value) is not int or value < 0 for mid, value in revisions.items()):
                raise ValueError("Invalid module revision")
            return data
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ModuleError("Module configuration is invalid; restore its last valid copy.", 503) from exc

    def enabled(self) -> set[str]:
        return set(self.snapshot()["enabled"])

    def get(self, mid: str) -> Manifest:
        if mid not in self.manifests:
            raise ModuleError("Unknown module", 404)
        return self.manifests[mid]

    def settings(self, mid: str, snapshot: dict | None = None, effective=False) -> dict:
        item = self.get(mid)
        values = {field.key: field.default for field in item.settings}
        if effective and item.activation == "build":
            values.update(self.applied_settings.get(mid, {}))
        else:
            values.update((snapshot or self.snapshot())["settings"].get(mid, {}))
        return values

    def active(self, mid: str, snapshot: dict | None = None) -> bool:
        item = self.get(mid)
        return mid in self.installed and (item.activation == "build" or mid in (snapshot or self.snapshot())["enabled"])

    def catalog(self):
        snapshot = self.snapshot()
        result = []
        for item in self.manifests.values():
            enabled = item.id in snapshot["enabled"]
            active = self.active(item.id, snapshot)
            settings = self.settings(item.id, snapshot)
            pending = item.activation == "build" and (enabled != active or (enabled and settings != self.settings(item.id, snapshot, effective=True)))
            result.append(dict(id=item.id, name=item.name, description=item.description, version=item.version,
                activation=item.activation, dependencies=item.dependencies, installed=item.id in self.installed,
                enabled=enabled, active=active, pending_build=pending, revision=snapshot["module_revisions"].get(item.id, 0),
                settings=settings, settings_schema=[field.model_dump() for field in item.settings],
                frontend=item.frontend.model_dump() if item.frontend else None))
        return result

    def require_enabled(self, mid: str) -> Manifest:
        item = self.get(mid)
        if not self.active(mid):
            raise ModuleError("Module is disabled or not installed", 404)
        return item

    def validate_settings(self, mid: str, values: dict):
        fields = {field.key: field for field in self.get(mid).settings}
        if not isinstance(values, dict) or set(values) - fields.keys():
            raise ModuleError("Unknown module setting", 422)
        for key, value in values.items():
            if not fields[key].accepts(value):
                raise ModuleError("Invalid module setting: " + key, 422)

    def update(self, mid: str, *, enabled: bool | None = None, settings: dict | None = None,
               expected_revision: int | None = None):
        """Caller owns an exclusive lease. Never deletes module data or credentials."""
        item = self.get(mid)
        data = self.snapshot()
        if expected_revision is not None and expected_revision != data["module_revisions"].get(mid, 0):
            raise ModuleError("Module settings changed in another window. Reload before saving.")
        if mid not in self.installed and item.activation != "build":
            raise ModuleError("Install this module first.")
        values = set(data["enabled"])
        if enabled is True:
            if not set(item.dependencies) <= values:
                raise ModuleError("Enable the required dependencies first.")
            values.add(mid)
        elif enabled is False:
            if any(mid in self.manifests[x].dependencies for x in values - {mid}):
                raise ModuleError("An enabled module depends on this module.")
            values.discard(mid)
        if settings is not None:
            self.validate_settings(mid, settings)
            data["settings"][mid] = {**data["settings"].get(mid, {}), **settings}
        data["module_revisions"][mid] = data["module_revisions"].get(mid, 0) + 1
        data.update(enabled=sorted(values), revision=data["revision"] + 1)
        self.state.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.state.parent, prefix=".modules-")
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.state)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def set_enabled(self, mid: str, enabled: bool):
        self.update(mid, enabled=enabled)

    @asynccontextmanager
    async def lock(self, exclusive=False):
        """Cross-worker lease: disabling cannot race an admitted proxy request."""
        await asyncio.to_thread(self.state.parent.mkdir, parents=True, exist_ok=True)
        stream = await asyncio.to_thread(open, self.state.with_suffix('.lock'), 'a')
        # Nonblocking polling remains cancellable (no leaked thread holding a lock).
        try:
            while True:
                try:
                    fcntl.flock(stream, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    await asyncio.sleep(0.05)
            yield
        finally:
            stream.close()
