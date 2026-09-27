"""Modular-monolith composition root and in-process query bus.

Modules share contracts, not storage or implementations. Native model processes
remain infrastructure adapters; enabling/disabling never terminates another app.
"""
from abc import ABC, abstractmethod
from copy import deepcopy

from open_notebook.modules.contracts import ModelPolicyRequest, ModelPolicyResult, SettingsQuery
from open_notebook.modules.registry import ModuleError, Registry


class Module(ABC):
    def __init__(self, registry: Registry, module_id: str):
        self.registry, self.id = registry, module_id

    @abstractmethod
    def handle(self, request: SettingsQuery | ModelPolicyRequest):
        """Return a detached value. Never expose a module's mutable state."""


class ConfiguredModule(Module):
    """Manifest-driven implementation of the public settings and model ports."""
    def handle(self, request: SettingsQuery | ModelPolicyRequest):
        if isinstance(request, SettingsQuery):
            self.registry.require_enabled(self.id)
            return deepcopy(self.registry.settings(self.id, effective=True))
        item = self.registry.get(self.id)
        defaults = {}
        for policy in item.model_policies:
            if (policy.provider != request.provider.replace("-", "_") or policy.model_type != request.model_type
                    or (policy.names and request.name not in policy.names)):
                continue
            if not self.registry.active(self.id):
                raise ModuleError(f"{item.name} is disabled. Enable it in Settings → Modules settings.")
            settings = self.registry.settings(self.id, effective=True)
            defaults.update({key: settings[value] for key, value in policy.config.items()})
        return ModelPolicyResult(defaults)


class ModuleBus:
    """Typed, synchronous request/reply. There is no arbitrary public RPC route."""
    def __init__(self, registry: Registry | None = None):
        self.registry = registry or Registry()
        self.modules: dict[str, Module] = {
            mid: ConfiguredModule(self.registry, mid) for mid in self.registry.manifests
            if mid in self.registry.installed
        }

    def query(self, request: SettingsQuery | ModelPolicyRequest):
        if isinstance(request, SettingsQuery):
            if request.module_id not in self.modules:
                raise ModuleError("Module is not installed", 404)
            return self.modules[request.module_id].handle(request)
        if isinstance(request, ModelPolicyRequest):
            defaults = {}
            for module in self.modules.values():
                result = module.handle(request)
                if defaults.keys() & result.config_defaults.keys():
                    raise ModuleError("Conflicting model configuration contributions", 503)
                defaults.update(result.config_defaults)
            return ModelPolicyResult(defaults)
        raise TypeError("Unsupported module contract")


def model_policy(provider: str, name: str, model_type: str, config: dict | None = None) -> dict:
    result = ModuleBus().query(ModelPolicyRequest(provider, name, model_type))
    # Call-specific options retain precedence. Disabled admission always fails.
    return {**(config or {}), **result.config_defaults}
