from __future__ import annotations

from math import ceil
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.core_entities import Task, User
from app.schemas.view import ViewCreate, ViewOut, ViewUpdate
from app.security import get_current_user
from app.crud.view import (
    create_view,
    delete_view as crud_delete_view,
    get_view,
    list_views as crud_list_views,
    update_view as crud_update_view,
)

router = APIRouter(prefix="/views", tags=["Views"])


# ----------------------------
# Helpers
# ----------------------------
def _scope_type_to_str(scope_type: Optional[object]) -> Optional[str]:
    if scope_type is None:
        return None
    return str(getattr(scope_type, "value", scope_type)).lower()


def _parse_sort(spec: Optional[str]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    if spec:
        for token in spec.split(","):
            token = token.strip()
            if not token:
                continue
            if ":" in token:
                f, d = token.split(":", 1)
            else:
                f, d = token, "asc"
            pairs.append((f.strip(), "desc" if d.lower() == "desc" else "asc"))
    if not pairs:
        pairs = [("name", "asc"), ("id", "asc")]
    return pairs


# ----------------------------
# CRUD endpoints (unchanged)
# ----------------------------
@router.get(
    "",
    response_model=List[ViewOut],
    summary="List my saved views (optionally by scope)",
)
def list_views(
    scope_type: Optional[str] = Query(default=None),
    scope_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud_list_views(
        db,
        owner_id=str(current_user.id),
        scope_type=_scope_type_to_str(scope_type),
        scope_id=scope_id,
    )


@router.post("", response_model=ViewOut, summary="Create a saved view (owner-only)")
def create_view_endpoint(
    data: ViewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_view(db, owner_id=str(current_user.id), data=data)


@router.get(
    "/{view_id}", response_model=ViewOut, summary="Get a saved view (owner-only)"
)
def get_view_endpoint(
    view_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    v = get_view(db, view_id)
    if not v or str(v.owner_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="View not found")
    return v


@router.patch(
    "/{view_id}", response_model=ViewOut, summary="Update a saved view (owner-only)"
)
def update_view_endpoint(
    view_id: str,
    data: ViewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    v = get_view(db, view_id)
    if not v or str(v.owner_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="View not found")
    return crud_update_view(db, v, data)


@router.delete("/{view_id}", summary="Delete a saved view (owner-only)")
def delete_view_endpoint(
    view_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    v = get_view(db, view_id)
    if not v or str(v.owner_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="View not found")
    crud_delete_view(db, v)
    return {"detail": "View deleted"}


# ----------------------------
# APPLY: /views/{id}/tasks
# ----------------------------
@router.get("/{view_id}/tasks", summary="Apply a saved view to tasks (list-scope only)")
def apply_view_to_tasks(
    view_id: str,
    sort: Optional[str] = Query(
        default=None, description="Override view.sort_spec, e.g. name:desc"
    ),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Authorize
    v = get_view(db, view_id)
    if not v or str(v.owner_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="View not found")

    if _scope_type_to_str(getattr(v, "scope_type", None)) != "list":
        raise HTTPException(
            status_code=400, detail="Only list-scoped views can be applied to tasks"
        )

    scope_id = str(getattr(v, "scope_id", "") or "").strip()
    if not scope_id:
        return {"total": 0, "pages": 0, "items": []}

    # Build a simple, direct query using the defined relationship.
    q = db.query(Task).filter(Task.list_id == scope_id)

    # Count BEFORE pagination
    total = q.count()
    if total == 0:
        return {"total": 0, "pages": 0, "items": []}

    # Sorting
    pairs = _parse_sort(sort or getattr(v, "sort_spec", None))
    orders = []
    for field, direction in pairs:
        col = getattr(Task, field, None)
        if col is None and field == "name":
            col = getattr(Task, "title", None)
        if col is not None:
            orders.append(desc(col) if direction == "desc" else asc(col))
    if getattr(Task, "id", None) is not None:
        orders.append(asc(getattr(Task, "id")))

    # Page slice
    start = (page - 1) * per_page
    rows = q.order_by(*orders).offset(start).limit(per_page).all()

    items = [
        {
            "id": str(getattr(t, "id", "")),
            "name": getattr(t, "name", None) or getattr(t, "title", None),
        }
        for t in rows
    ]
    return {"total": total, "pages": ceil(total / per_page), "items": items}
