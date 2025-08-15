# File: /app/core/logging.py | Version: 1.1 | Title: App logging configuration (quiet httpx; JSON optional)
import json
import logging
import logging.config
import os


def _boolenv(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    use_json = _boolenv("LOG_JSON", False)

    if use_json:
        fmt = "%(message)s"
        formatter = {
            "format": fmt,
            "class": "logging.Formatter",
        }
    else:
        fmt = "%(levelname)s %(asctime)s %(name)s: %(message)s"
        formatter = {
            "format": fmt,
            "class": "logging.Formatter",
        }

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": formatter,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
        "loggers": {
            # Quiet overly chatty libraries during tests to avoid closed-stream errors
            "httpx": {"level": "WARNING", "propagate": False},
            "httpcore": {"level": "WARNING", "propagate": False},
            "uvicorn": {"level": level},
            "uvicorn.error": {"level": level},
            "uvicorn.access": {"level": level},
            "sqlalchemy.engine": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(config)

    if use_json:

        class JsonConsole(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                base = {
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    base["exc_info"] = self.formatException(record.exc_info)
                return json.dumps(base, ensure_ascii=False)

        # Apply JSON formatter safely to all root handlers
        for h in logging.getLogger().handlers:
            h.setFormatter(JsonConsole())
