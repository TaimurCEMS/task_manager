# File: app/db/__init__.py | Version: 1.0 | Path: /app/db/__init__.py
# Re-export commonly used items so tests can do: from app.db import Base, get_db
# Import models so SQLAlchemy Base knows about them when metadata is created
# (This prevents "no tables" issues if tests create tables from Base without importing models)
import app.models  # noqa: F401

from .base_class import Base
from .session import SessionLocal, engine, get_db

__all__ = ["Base", "get_db", "SessionLocal", "engine"]
