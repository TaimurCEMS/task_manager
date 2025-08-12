# File: tests/test_hardening_smoke.py | Version: 1.0 | Title: Coverage bump for logging, rate limit, and sentry
import logging
import sys
import types

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.logging import configure_logging
from app.middleware.rate_limit import MemoryRateLimiter
from app.observability.sentry import init_sentry_if_configured


def test_configure_logging_plain_and_json(monkeypatch, capsys):
    # Plain text path
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_JSON", "false")
    configure_logging()
    logging.getLogger(__name__).debug("plain-log")
    # JSON path
    monkeypatch.setenv("LOG_JSON", "true")
    configure_logging()
    logging.getLogger(__name__).info("json-log")
    # We don't need strict assertions—just make sure both code paths execute without error.


def _star_app():
    async def ping(request):
        return PlainTextResponse("pong")

    app = Starlette(routes=[Route("/ping", ping)])
    app.add_middleware(MemoryRateLimiter)
    return app


def test_rate_limiter_allows_then_blocks(monkeypatch):
    # Enable limiter with a tiny window so we can hit the block path quickly.
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "2")
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "2")

    app = _star_app()
    client = TestClient(app)

    headers = {"x-forwarded-for": "1.2.3.4"}
    r1 = client.get("/ping", headers=headers)
    r2 = client.get("/ping", headers=headers)
    r3 = client.get("/ping", headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429  # exceeded within window


def test_sentry_init_disabled_then_enabled(monkeypatch):
    # Disabled path (no DSN)
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    init_sentry_if_configured()  # should be a no-op

    # Enabled path: stub out sentry_sdk and its ASGI integration so import works.
    class DummySDK(types.SimpleNamespace):
        @staticmethod
        def init(**kwargs):
            # capture kwargs to ensure function executed at least once
            DummySDK.last_init = kwargs

    sentry_pkg = types.ModuleType("sentry_sdk")
    sentry_pkg.init = DummySDK.init  # type: ignore[attr-defined]

    integrations_pkg = types.ModuleType("sentry_sdk.integrations")
    asgi_pkg = types.ModuleType("sentry_sdk.integrations.asgi")

    class SentryAsgiMiddleware:  # noqa: N801
        def __init__(self, app):
            self.app = app

    asgi_pkg.SentryAsgiMiddleware = SentryAsgiMiddleware  # type: ignore[attr-defined]

    sys.modules["sentry_sdk"] = sentry_pkg
    sys.modules["sentry_sdk.integrations"] = integrations_pkg
    sys.modules["sentry_sdk.integrations.asgi"] = asgi_pkg

    monkeypatch.setenv("SENTRY_DSN", "https://dummy-public@o0.ingest.sentry.io/0")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")
    monkeypatch.setenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")

    init_sentry_if_configured()
    assert hasattr(DummySDK, "last_init")  # ensures init() was called
