# File: app/middleware/rate_limit.py | Version: 1.0 | Title: Lightweight in-memory rate limiting middleware
import os
import time
from collections import deque
from typing import Deque, Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def _boolenv(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


class MemoryRateLimiter(BaseHTTPMiddleware):
    """
    Simple token-bucket style limiter (per-IP per-path).
    Off by default; enable via RATE_LIMIT_ENABLED=true.

    Env:
      RATE_LIMIT_WINDOW_SECONDS (default 60)
      RATE_LIMIT_MAX_REQUESTS    (default 120)
    """

    def __init__(self, app):
        super().__init__(app)
        self.enabled = _boolenv("RATE_LIMIT_ENABLED", False)
        self.window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        self.max_req = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
        self._buckets: Dict[Tuple[str, str], Deque[float]] = {}

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        client_ip = (
            request.headers.get("x-forwarded-for") or request.client.host or "unknown"
        )
        key = (client_ip, request.url.path)
        now = time.time()
        window_start = now - self.window

        bucket = self._buckets.setdefault(key, deque())
        # purge old
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self.max_req:
            retry_after = max(1, int(bucket[0] + self.window - now))
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)
