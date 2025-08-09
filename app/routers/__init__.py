# File: /app/routers/__init__.py | Version: 1.1 | Path: /app/routers/__init__.py
"""
Router package exports.

Keeping these explicit helps static analyzers and avoids surprises
when importing submodules like: `from app.routers import task as task_router`.
"""
from . import auth, core_entities, task

__all__ = ["auth", "core_entities", "task"]
