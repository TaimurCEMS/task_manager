# File: app/routers/health.py | Version: 1.0 | Title: Health & readiness endpoints
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import engine

router = APIRouter(tags=["Health"])


@router.get("/healthz")
def healthz() -> dict:
    """
    Liveness probe: returns 200 if the app can serve requests.
    """
    return {"status": "ok"}


@router.get("/readyz")
def readyz():
    """
    Readiness probe: 200 if DB is reachable (SELECT 1 succeeds), else 503.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except (
        Exception
    ):  # pragma: no cover — we cover success path; error path is best-effort
        return JSONResponse({"status": "degraded", "db": "error"}, status_code=503)
