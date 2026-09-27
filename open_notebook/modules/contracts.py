"""Public, versioned module contracts. No module may import another's internals."""
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Scalar = str | int | bool


class SettingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    kind: Literal["boolean", "integer", "choice", "text"]
    default: Scalar
    label_key: str
    help_key: str
    minimum: int | None = None
    maximum: int | None = None
    options: list[str] = Field(default_factory=list)

    def accepts(self, value: object) -> bool:
        if self.kind == "boolean":
            return type(value) is bool
        if self.kind == "integer":
            return type(value) is int and (self.minimum is None or value >= self.minimum) and (self.maximum is None or value <= self.maximum)
        if self.kind == "choice":
            return isinstance(value, str) and value in self.options
        return isinstance(value, str) and 1 <= len(value.strip()) <= 120

    @model_validator(mode="after")
    def valid_default(self):
        if not self.accepts(self.default):
            raise ValueError("Invalid setting default")
        return self


class ModelPolicySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    model_type: str
    names: list[str] = Field(default_factory=list)
    config: dict[str, str] = Field(default_factory=dict)  # config key -> setting key


@dataclass(frozen=True)
class SettingsQuery:
    """v1: only applied modules expose their effective public settings."""
    module_id: str


@dataclass(frozen=True)
class ModelPolicyRequest:
    """v1: synchronous admission of a NEW model operation, no credential transport."""
    provider: str
    name: str
    model_type: str


@dataclass(frozen=True)
class ModelPolicyResult:
    config_defaults: dict[str, Scalar] = field(default_factory=dict)
