# File: /app/models/view.py | Version: 1.1 | Title: SQLAlchemy model for Saved Views
from __future__ import annotations

import uuid
from sqlalchemy import Boolean, Column, DateTime, String, JSON, func, Index
from app.db.base_class import Base


class View(Base):
    __tablename__ = "views"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, nullable=False)

    # Scope where this view applies: "workspace" | "space" | "list"
    scope_type = Column(String, nullable=False)
    scope_id = Column(String, nullable=False)

    name = Column(String, nullable=False)

    filters_json = Column(JSON, nullable=True)
    sort_spec = Column(String, nullable=True)
    columns_json = Column(JSON, nullable=True)

    is_default = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_views_owner", "owner_id"),
        Index("ix_views_scope", "scope_type", "scope_id"),
    )
