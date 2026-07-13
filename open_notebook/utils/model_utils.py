"""Utilities for working with Pydantic models."""

from pydantic import BaseModel


def full_model_dump(model):
    """Recursively dump Pydantic models nested inside dicts/lists to plain data."""
    if isinstance(model, BaseModel):
        return model.model_dump()
    elif isinstance(model, dict):
        return {k: full_model_dump(v) for k, v in model.items()}
    elif isinstance(model, list):
        return [full_model_dump(item) for item in model]
    else:
        return model
