# File: /app/routers/views_apply.py | Version: 0.1 | Title: Deprecated (no routes) — apply endpoint now lives in /app/routers/views.py
from fastapi import APIRouter

# Keep a router object so include_router(...) doesn’t blow up,
# but define NO routes here. The apply endpoint is in app/routers/views.py.
router = APIRouter(prefix="/views", tags=["Views Apply (deprecated)"])
