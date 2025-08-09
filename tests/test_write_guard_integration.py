# File: /tests/test_write_guard_integration.py | Version: 1.0
from typing import Dict

from sqlalchemy.orm import Session

from app.models.core_entities import WorkspaceMember, User  # type: ignore


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client, email: str, password: str = "pass123") -> str:
    # register
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201)
    # login
    r = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    token = r.json().get("access_token")
    assert token, "No access_token returned"
    return token


def test_write_requires_membership__outsider_403_then_member_200(client, db_session: Session):
    """
    Flow:
      - User1 registers (auto-creates Workspace A; is Owner).
      - User2 tries to create a Space in Workspace A -> 403 (not a member).
      - We add User2 as Member in Workspace A (DB insert).
      - User2 retries -> 200.
    """
    # Users
    u1_email = "owner@example.com"
    u2_email = "outsider@example.com"

    token_u1 = _register_and_login(client, u1_email)
    token_u2 = _register_and_login(client, u2_email)

    # Find Workspace A (created for User1 on register)
    r = client.get("/workspaces/", headers=_auth_headers(token_u1))
    assert r.status_code == 200, r.text
    workspaces = r.json()
    assert isinstance(workspaces, list) and len(workspaces) >= 1
    workspace_id = workspaces[0]["id"]

    # 1) Outsider tries to create a Space -> should be 403
    payload = {"name": "Secured Space", "workspace_id": workspace_id}
    r = client.post("/spaces/", json=payload, headers=_auth_headers(token_u2))
    assert r.status_code == 403, f"Expected 403 for outsider, got {r.status_code}: {r.text}"

    # 2) Add User2 as MEMBER in Workspace A (DB insert)
    user2 = db_session.query(User).filter(User.email == u2_email).first()
    assert user2, "User2 not found after registration"
    db_session.add(
        WorkspaceMember(
            user_id=str(user2.id),
            workspace_id=str(workspace_id),
            role="Member",
        )
    )
    db_session.commit()

    # 3) Retry as Member -> should be 200
    r = client.post("/spaces/", json=payload, headers=_auth_headers(token_u2))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Secured Space"
    assert str(body["workspace_id"]) == str(workspace_id)
