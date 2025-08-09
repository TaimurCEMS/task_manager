# File: /tests/test_subtasks.py | Version: 1.0 | Path: /tests/test_subtasks.py
from uuid import UUID
from typing import Dict

import pytest

from sqlalchemy.orm import Session

from app.crud import task as crud_task
from app.models.core_entities import WorkspaceMember, User  # type: ignore


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client, email: str, password: str = "pass123") -> str:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    r = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    assert token
    return token


def _bootstrap_workspace_space_list(client, token: str):
    # Grab the auto-created workspace for the logged-in user
    r = client.get("/workspaces/", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    ws = r.json()[0]
    workspace_id = ws["id"]

    # Create a space
    r = client.post(
        "/spaces/",
        json={"name": "Main Space", "workspace_id": workspace_id},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    space = r.json()

    # Create a list
    r = client.post(
        "/lists/",
        json={"name": "Main List", "space_id": space["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    lst = r.json()

    return workspace_id, space, lst


def _create_parent_task(client, token: str, list_id: str, space_id: str):
    r = client.post(
        "/tasks/",
        json={
            "name": "Parent Task",
            "description": "root",
            "status": "to_do",
            "priority": "Normal",
            "list_id": list_id,
            "space_id": space_id,
        },
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_create_and_list_subtasks(client):
    # User1 bootstraps workspace/space/list and a parent task
    token = _register_and_login(client, "owner+subtasks@example.com")
    workspace_id, space, lst = _bootstrap_workspace_space_list(client, token)
    parent = _create_parent_task(client, token, lst["id"], space["id"])

    # Create a subtask under the parent (router enforces same list)
    r = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={
            "name": "Child A",
            "description": "child",
            "status": "to_do",
            "priority": "Normal",
            "list_id": lst["id"],   # will be overridden to parent list (same value)
            "space_id": space["id"] # required by schema; router rebuilds payload
        },
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    child = r.json()
    assert str(child["parent_task_id"]) == str(parent["id"])
    assert str(child["list_id"]) == str(lst["id"])

    # List back the subtasks
    r = client.get(f"/tasks/{parent['id']}/subtasks", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    children = r.json()
    assert isinstance(children, list) and len(children) == 1
    assert str(children[0]["id"]) == str(child["id"])


def test_create_subtask_requires_membership(client, db_session: Session):
    # User1 owns workspace; User2 is an outsider
    token_u1 = _register_and_login(client, "owner+guard@example.com")
    token_u2 = _register_and_login(client, "outsider+guard@example.com")

    workspace_id, space, lst = _bootstrap_workspace_space_list(client, token_u1)
    parent = _create_parent_task(client, token_u1, lst["id"], space["id"])

    # Outsider tries to create subtask -> 403
    r = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={
            "name": "Should Fail",
            "list_id": lst["id"],
            "space_id": space["id"],
        },
        headers=_auth_headers(token_u2),
    )
    assert r.status_code == 403, r.text

    # Add User2 as Member, retry -> 200
    user2 = db_session.query(User).filter(User.email == "outsider+guard@example.com").first()
    db_session.add(WorkspaceMember(workspace_id=workspace_id, user_id=user2.id, role="Member", is_active=True))
    db_session.commit()

    r = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={
            "name": "Now Works",
            "list_id": lst["id"],
            "space_id": space["id"],
        },
        headers=_auth_headers(token_u2),
    )
    assert r.status_code == 200, r.text


def test_move_subtask_cycle_prevention(client, db_session: Session):
    token = _register_and_login(client, "owner+cycle@example.com")
    _, space, lst = _bootstrap_workspace_space_list(client, token)

    # Create parent via API
    parent = _create_parent_task(client, token, lst["id"], space["id"])
    parent_id = UUID(parent["id"])

    # Create child via API (as subtask)
    r = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={"name": "Child", "list_id": lst["id"], "space_id": space["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    child = r.json()
    child_id = UUID(child["id"])

    # Try to move parent under child -> should raise ValueError (cycle)
    with pytest.raises(ValueError):
        crud_task.move_subtask(db_session, child_task_id=parent_id, new_parent_task_id=child_id)
