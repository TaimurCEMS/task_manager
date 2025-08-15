# tests/test_views_apply_router.py
from __future__ import annotations

from typing import Optional
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Import the function-under-test directly (bypass HTTP client)
from app.routers.views import apply_view_to_tasks
from app.models.core_entities import User, Workspace, Space, List as ListModel, Task
from app.models.view import View as ViewModel


def _get_or_create_user(db: Session, email: str) -> User:
    """Create (or fetch) a simple active user directly in the DB."""
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(email=email, hashed_password="fake-hash-for-test", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _seed_scope_with_list(
    db: Session, owner_id: str
) -> tuple[Workspace, Space, ListModel]:
    """Create a workspace -> space -> list chain and return them (IDs flushed)."""
    ws = Workspace(name="W", owner_id=owner_id)
    db.add(ws)
    db.flush()

    sp = Space(name="S", workspace_id=ws.id)
    db.add(sp)
    db.flush()

    lst = ListModel(name="L", space_id=sp.id)
    db.add(lst)
    db.flush()

    return ws, sp, lst


def _add_tasks(db: Session, list_id: str, names: list[str]) -> None:
    """Add tasks to a list; does not commit."""
    for nm in names:
        db.add(Task(name=nm, list_id=list_id))


def _make_view(
    db: Session,
    *,
    owner_id: str,
    scope_type: str,
    scope_id: Optional[str],
    sort_spec: Optional[str] = None,
) -> ViewModel:
    """Create a View row (committed & refreshed)."""
    v = ViewModel(
        name="My View",
        owner_id=owner_id,
        scope_type=scope_type,
        scope_id=scope_id,
        sort_spec=sort_spec,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def test_apply_view_lists_tasks_sorted_and_paged(db_session: Session):
    """
    Happy path: list-scoped view, stable sort by name then id, and paging.
    Calls the router function directly with a DB session and current_user,
    ensuring the test sees committed data without HTTP-layer concerns.
    """
    # Seed data
    user = _get_or_create_user(db_session, "vapply@example.com")
    _, _, lst = _seed_scope_with_list(db_session, user.id)

    _add_tasks(db_session, lst.id, ["Bravo", "Alpha", "Charlie"])
    view = _make_view(
        db_session,
        owner_id=user.id,
        scope_type="list",
        scope_id=lst.id,
        sort_spec="name:asc",
    )

    # Page 1 (2 per page): expect Alpha, Bravo
    result1 = apply_view_to_tasks(
        view_id=view.id,
        sort=None,
        page=1,
        per_page=2,
        db=db_session,
        current_user=user,
    )
    assert result1["total"] == 3
    assert result1["pages"] == 2
    assert [it["name"] for it in result1["items"]] == ["Alpha", "Bravo"]

    # Page 2: expect Charlie
    result2 = apply_view_to_tasks(
        view_id=view.id,
        sort=None,
        page=2,
        per_page=2,
        db=db_session,
        current_user=user,
    )
    assert [it["name"] for it in result2["items"]] == ["Charlie"]

    # Override sort to desc
    result3 = apply_view_to_tasks(
        view_id=view.id,
        sort="name:desc",
        page=1,
        per_page=3,
        db=db_session,
        current_user=user,
    )
    assert [it["name"] for it in result3["items"]] == ["Charlie", "Bravo", "Alpha"]


def test_apply_view_rejects_non_owner(db_session: Session):
    """
    Non-owner should receive a 404 (owner-only semantics).
    """
    owner = _get_or_create_user(db_session, "owner@example.com")
    intruder = _get_or_create_user(db_session, "intruder@example.com")
    _, _, lst = _seed_scope_with_list(db_session, owner.id)
    _add_tasks(db_session, lst.id, ["One"])
    view = _make_view(
        db_session,
        owner_id=owner.id,
        scope_type="list",
        scope_id=lst.id,
        sort_spec="name:asc",
    )

    with pytest.raises(HTTPException) as ex:
        _ = apply_view_to_tasks(
            view_id=view.id,
            sort=None,
            page=1,
            per_page=10,
            db=db_session,
            current_user=intruder,
        )
    assert ex.value.status_code == 404
    assert "View not found" in ex.value.detail


def test_apply_view_rejects_non_list_scope(db_session: Session):
    """
    Only 'list'-scoped views can be applied to tasks; any other scope returns 400.
    """
    user = _get_or_create_user(db_session, "scoper@example.com")
    ws, sp, _ = _seed_scope_with_list(db_session, user.id)  # we’ll use the space scope

    view = _make_view(
        db_session,
        owner_id=user.id,
        scope_type="space",  # not 'list'
        scope_id=sp.id,
        sort_spec="name:asc",
    )

    with pytest.raises(HTTPException) as ex:
        _ = apply_view_to_tasks(
            view_id=view.id,
            sort=None,
            page=1,
            per_page=10,
            db=db_session,
            current_user=user,
        )
    assert ex.value.status_code == 400
    assert "Only list-scoped views" in ex.value.detail
