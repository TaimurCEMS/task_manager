# File: /app/main.py | Version: 1.4 | Title: FastAPI App (safe router includes)
from __future__ import annotations

import importlib
import importlib.util
from fastapi import FastAPI

# Optional: show algo in title if settings import works
try:
    from app.core.config import settings
    _title = f"Task Manager API ({settings.ALGORITHM})"
except Exception:
    _title = "Task Manager API"

app = FastAPI(title=_title)


def include_if_exists(module_path: str, attr_name: str = "router") -> bool:
    """
    Import module_path if present and include its `router` into the app.
    Returns True if a router was included.
    """
    spec = importlib.util.find_spec(module_path)
    if not spec:
        return False
    mod = importlib.import_module(module_path)
    router = getattr(mod, attr_name, None)
    if router is not None:
        app.include_router(router)
        return True
    return False


# ✅ Required routers (these should exist in your repo)
include_if_exists("app.routers.auth")
include_if_exists("app.routers.core_entities")
include_if_exists("app.routers.task")
include_if_exists("app.routers.tags")
include_if_exists("app.routers.tasks_filter")
include_if_exists("app.routers.custom_fields")

# 🟡 Optional routers (include only if present)
include_if_exists("app.routers.comments")
include_if_exists("app.routers.watchers")
include_if_exists("app.routers.time_tracking")
