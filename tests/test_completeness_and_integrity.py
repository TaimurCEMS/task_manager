# tests/test_completeness_and_integrity.py
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.routers.views import apply_view_to_tasks
from app.models.core_entities import User, Workspace, Space, List as ListModel, Task
from app.models.view import View as ViewModel


def _get_or_create_user(db: Session, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, hashed_password="x")
        db.add(user)
        db.flush()
    return user


def _bootstrap_scope(db: Session, owner: User):
    ws = Workspace(name="WS", owner_id=str(owner.id))
    db.add(ws)
    db.flush()
    sp = Space(name="SP", workspace_id=str(ws.id))
    db.add(sp)
    db.flush()
    lst = ListModel(name="L1", space_id=str(sp.id))
    db.add(lst)
    db.flush()
    return ws, sp, lst


def test_apply_view_owner_only_and_scope_validation_and_stability(db_session: Session):
    # Two users
    owner = _get_or_create_user(db_session, "owner@example.com")
    stranger = _get_or_create_user(db_session, "stranger@example.com")

    # Scope
    ws, sp, lst = _bootstrap_scope(db_session, owner)

    # Two tasks with identical names to exercise tiebreaker-by-id
    for _ in range(2):
        db_session.add(Task(name="Same", list_id=str(lst.id)))
    # And one more unique task to ensure counting doesn't break
    db_session.add(Task(name="Another", list_id=str(lst.id)))
    db_session.flush()

    # Good list-scoped view owned by `owner`
    view = ViewModel(
        name="V1",
        owner_id=str(owner.id),
        scope_type="list",
        scope_id=str(lst.id),
        sort_spec="name:asc",
    )
    db_session.add(view)
    db_session.flush()

    # 1) Owner-only: a non-owner should get a 404 to avoid leaking existence
    with pytest.raises(HTTPException) as excinfo:
        apply_view_to_tasks(
            str(view.id),
            sort=None,
            page=1,
            per_page=10,
            db=db_session,
            current_user=stranger,
        )
    assert excinfo.value.status_code == 404

    # 2) As owner, applying should return all 3 tasks and be deterministic
    res = apply_view_to_tasks(
        str(view.id),
        sort=None,
        page=1,
        per_page=10,
        db=db_session,
        current_user=owner,
    )
    assert res["total"] == 3
    assert res["pages"] == 1
    assert [it["name"] for it in res["items"]] == ["Another", "Same", "Same"]
    # When names tie, ids must be in ascending order for stability
    tied_ids = [it["id"] for it in res["items"] if it["name"] == "Same"]
    assert tied_ids == sorted(tied_ids)

    # 3) A non-list-scoped view must be rejected with 400
    bad_view = ViewModel(
        name="VBad",
        owner_id=str(owner.id),
        scope_type="workspace",
        scope_id=str(ws.id),
        sort_spec="name:asc",
    )
    db_session.add(bad_view)
    db_session.flush()
    with pytest.raises(HTTPException) as excinfo2:
        apply_view_to_tasks(
            str(bad_view.id),
            sort=None,
            page=1,
            per_page=10,
            db=db_session,
            current_user=owner,
        )
    assert excinfo2.value.status_code == 400
