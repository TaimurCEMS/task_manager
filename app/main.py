# File: /app/main.py | Version: 1.10 | Title: FastAPI App (router includes + Saved Views Apply + quieter multipart logs)
from __future__ import annotations

import importlib
import importlib.util
import logging

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.rate_limit import MemoryRateLimiter
from app.observability.sentry import init_sentry_if_configured

# Initialize logging & observability
configure_logging()
# Silence very verbose multipart parser logs to avoid pytest "closed file" noise
logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)
init_sentry_if_configured()

# App
app = FastAPI(title=f"Task Manager API ({settings.ALGORITHM})")
app.add_middleware(MemoryRateLimiter)  # no-op unless RATE_LIMIT_ENABLED=true


def include_if_exists(module_path: str, attr_name: str = "router") -> bool:
    spec = importlib.util.find_spec(module_path)
    if not spec:
        return False
    mod = importlib.import_module(module_path)
    router = getattr(mod, attr_name, None)
    if router is not None:
        app.include_router(router)
        return True
    return False


# Required routers
include_if_exists("app.routers.auth")
include_if_exists("app.routers.core_entities")
include_if_exists("app.routers.task")
include_if_exists("app.routers.tags")
include_if_exists("app.routers.tasks_filter")
include_if_exists("app.routers.custom_fields")

# Optional routers
include_if_exists("app.routers.comments")
include_if_exists("app.routers.watchers")
include_if_exists("app.routers.time_tracking")
include_if_exists("app.routers.auth_extras")
include_if_exists("app.routers.health")
include_if_exists("app.routers.views")  # Saved Views CRUD (collection: /views)
include_if_exists("app.routers.views_apply")  # Apply a Saved View to tasks

# Optional standardized error responses
if getattr(settings, "ENABLE_STD_ERRORS", False):
    from app.core.error_handlers import register_exception_handlers

    register_exception_handlers(app)
