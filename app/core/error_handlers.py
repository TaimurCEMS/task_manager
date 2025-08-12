# File: /app/core/error_handlers.py | Version: 1.0 | Title: Standardized Error Handlers (optional)
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    500: "INTERNAL_SERVER_ERROR",
}


def _err(code: int, message: str):
    return {"error": {"code": _CODE_MAP.get(code, "ERROR"), "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(_req: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code, content=_err(exc.status_code, str(exc.detail))
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(_req: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content=_err(422, "Validation error"))

    @app.exception_handler(Exception)
    async def _unhandled(_req: Request, exc: Exception):
        # Avoid leaking internals
        return JSONResponse(status_code=500, content=_err(500, "Internal server error"))
