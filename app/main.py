from __future__ import annotations
from fastapi import FastAPI
import importlib
from typing import Optional

def _include_optional_router(app: FastAPI, module_path: str, attr_name: str = "router") -> Optional[object]:
    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, attr_name, None)
        if router is not None:
            app.include_router(router)
            return router
    except Exception:
        return None

app = FastAPI(title="Task Manager API")

# Core routers
_include_optional_router(app, "app.routers.auth")
_include_optional_router(app, "app.routers.core_entities")
_include_optional_router(app, "app.routers.task")
_include_optional_router(app, "app.routers.tags")
_include_optional_router(app, "app.routers.tasks_filter")
# NEW: Add the custom fields router
_include_optional_router(app, "app.routers.custom_fields")

# Optional / future routers
_include_optional_router(app, "app.routers.comments")
_include_optional_router(app, "app.routers.watchers")
_include_optional_router(app, "app.routers.time_tracking")
