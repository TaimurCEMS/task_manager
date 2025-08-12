# File: app/core/logging.py | Version: 1.0 | Title: App logging configuration (JSON optional)
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
            "uvicorn": {"level": level},
            "uvicorn.error": {"level": level},
            "uvicorn.access": {"level": level},
            "sqlalchemy.engine": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(config)
    if use_json:
        # Wrap LogRecord into JSON message (simple, zero-deps)
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

        logging.getLogger().handlers[0].setFormatter(JsonConsole())
