"""
Domain models for Open Notebook.

This module exports the core domain models used throughout the application.
"""

from open_notebook.domain.workspace import Workspace, WorkspaceMember

__all__: list[str] = [
    "Workspace",
    "WorkspaceMember",
]
