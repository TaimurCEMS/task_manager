# File: /tests/test_comments_api.py | Version: 1.0 | Path: /tests/test_comments_api.py
from typing import Dict, Tuple

# These tests assume you already have a `client` fixture (TestClient) from conftest.py
# and standard auth endpoints using OAuth2 password flow.
# If any endpoint names differ in your app, tell me the failing line and I’ll tailor quickly.

# -------- helpers --------

def _register(client, email: str, password: str = "Passw0rd!", full_name: str = "Test User"):
    r = client.post("/auth/register", json={"email": email, "password": password, "full_name": full_name})
    assert r.status_code in (200, 201), r.text
    return r.json()

def _login_token(client, email: str, password: str = "Passw0rd!") -> str:
    """
    Try standard OAuth2 token endpoint first; fall back to /auth/login if your app uses that.
    """
    # try /auth/token (OAuth2 Password)
    r = client.post(
        "/auth/token",
        data={"username": email, "password": password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code == 200 and "access_token" in r.json():
        return r.json()["access_token"]

    # fallback: /auth/login (JSON)
    r = client.post("/auth/login", json={"username": email, "password": password})
    assert r.status_code == 200 and "access_token" in r.json(), r.text
    return r.json()["access_token"]

def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def _create_workspace_space_list_task(client, headers) -> Tuple[str, str, str, str]:
    # Workspace
    r = client.post("/workspaces/", json={"name": "W"}, headers=headers)
    assert r.status_code in (200, 201), r.text
    wid = r.json()["id"]

    # Space
    r = client.post("/spaces/", json={"name": "S", "workspace_id": wid}, headers=headers)
    assert r.status_code in (200, 201), r.text
    sid = r.json()["id"]

    # List
    r = client.post("/lists/", json={"name": "L", "space_id": sid}, headers=headers)
    assert r.status_code in (200, 201), r.text
    lid = r.json()["id"]

    # Task
    payload = {"name": "T1", "space_id": sid, "list_id": lid}
    r = client.post("/tasks/", json=payload, headers=headers)
    assert r.status_code in (200, 201), r.text
    tid = r.json()["id"]

    return wid, sid, lid, tid

# -------- tests --------

def test_comments_create_and_list(client):
    # Owner registers & logs in
    _register(client, "owner@example.com")
    owner_token = _login_token(client, "owner@example.com")
    owner_headers = _auth_headers(owner_token)

    # Build minimal hierarchy and a task
    _, _, _, task_id = _create_workspace_space_list_task(client, owner_headers)

    # Create a comment
    r = client.post(f"/tasks/{task_id}/comments", json={"body": "First!"}, headers=owner_headers)
    assert r.status_code in (200, 201), r.text
    comment = r.json()
    assert comment["task_id"] == task_id
    assert comment["body"] == "First!"
    assert "id" in comment

    # List comments
    r = client.get(f"/tasks/{task_id}/comments", headers=owner_headers)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert any(c["body"] == "First!" for c in items)

def test_comments_forbidden_for_outsider(client):
    # Owner creates workspace + task
    _register(client, "owner2@example.com")
    owner_token = _login_token(client, "owner2@example.com")
    owner_headers = _auth_headers(owner_token)
    _, _, _, task_id = _create_workspace_space_list_task(client, owner_headers)

    # Outsider (not a member of the owner's workspace)
    _register(client, "outsider@example.com")
    outsider_token = _login_token(client, "outsider@example.com")
    outsider_headers = _auth_headers(outsider_token)

    # Outsider tries to POST a comment -> 403
    r = client.post(f"/tasks/{task_id}/comments", json={"body": "Hello"}, headers=outsider_headers)
    assert r.status_code == 403, r.text

    # Outsider tries to GET comments -> 403
    r = client.get(f"/tasks/{task_id}/comments", headers=outsider_headers)
    assert r.status_code == 403, r.text
