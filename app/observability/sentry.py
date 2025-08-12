# File: app/observability/sentry.py | Version: 1.0 | Title: Optional Sentry initialization
import logging
import os

log = logging.getLogger(__name__)


def init_sentry_if_configured() -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        log.info("Sentry disabled (no SENTRY_DSN).")
        return

    try:
        import sentry_sdk

        traces = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        profiles = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0"))

        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=traces,
            profiles_sample_rate=profiles,
            enable_tracing=traces > 0.0,
        )
        log.info("Sentry initialized.")
    except Exception as e:  # pragma: no cover (best-effort)
        log.warning("Sentry init failed: %s", e)
