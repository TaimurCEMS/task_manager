# File: /app/crud/view.py | Version: 1.1 | Title: CRUD helpers for Saved Views
from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.view import View


def create_view(db: Session, owner_id: str, data) -> View:
    v = View(
        owner_id=owner_id,
        scope_type=data.scope_type,
        scope_id=data.scope_id,
        name=data.name,
        filters_json=data.filters_json,
        sort_spec=data.sort_spec,
        columns_json=data.columns_json,
        is_default=bool(data.is_default),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def get_view(db: Session, view_id: str) -> Optional[View]:
    return db.query(View).filter(View.id == view_id).first()


def list_views(
    db: Session, owner_id: str, scope_type: str, scope_id: str
) -> List[View]:
    return (
        db.query(View)
        .filter(
            View.owner_id == owner_id,
            View.scope_type == scope_type,
            View.scope_id == scope_id,
        )
        .order_by(View.is_default.desc(), View.created_at.desc())
        .all()
    )


def update_view(db: Session, v: View, data) -> View:
    if getattr(data, "name", None) is not None:
        v.name = data.name
    if getattr(data, "filters_json", None) is not None:
        v.filters_json = data.filters_json
    if getattr(data, "sort_spec", None) is not None:
        v.sort_spec = data.sort_spec
    if getattr(data, "columns_json", None) is not None:
        v.columns_json = data.columns_json
    if getattr(data, "is_default", None) is not None:
        v.is_default = bool(data.is_default)
    db.commit()
    db.refresh(v)
    return v


def delete_view(db: Session, v: View) -> bool:
    db.delete(v)
    db.commit()
    return True
