# File: /tests/test_comments_api.py | Version: 1.1 | Path: /tests/test_comments_api.py
from typing import Dict, Tuple

def _register(client, email: str, password: str = "Passw0rd!", full_name: str = "Test User"):
    r = client.post("/auth/register", json={"email": email, "password": password, "full_name": full_name})
    assert r.status_code in (200, 201), r.text
    return r.json()

def _login_token(client, email: str, password: str = "Passw0rd!") -> str:
    r = client.post(
        "/auth/token",
        data={"username": email, "password": password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code == 200 and "access_token" in r.json():
        return r.json()["access_token"]
    r = client.post("/auth/login", json={"username": email, "password": password})
    assert r.status_code == 200 and "access_token" in r.json(), r.text
    return r.json()["access_token"]

def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def _create_workspace_space_list_task(client, headers) -> Tuple[str, str, str, str]:
    r = client.post("/workspaces/", json={"name": "W"}, headers=headers); assert r.status_code in (200, 201), r.text
    wid = r.json()["id"]
    r = client.post("/spaces/", json={"name": "S", "workspace_id": wid}, headers=headers); assert r.status_code in (200, 201), r.text
    sid = r.json()["id"]
    r = client.post("/lists/", json={"name": "L", "space_id": sid}, headers=headers); assert r.status_code in (200, 201), r.text
    lid = r.json()["id"]
    payload = {"name": "T1", "space_id": sid, "list_id": lid}
    r = client.post("/tasks/", json=payload, headers=headers); assert r.status_code in (200, 201), r.text
    tid = r.json()["id"]
    return wid, sid, lid, tid

def test_comments_create_and_list(client):
    _register(client, "owner@example.com")
    owner_token = _login_token(client, "owner@example.com")
    owner_headers = _auth_headers(owner_token)
    _, _, _, task_id = _create_workspace_space_list_task(client, owner_headers)

    r = client.post(f"/tasks/{task_id}/comments", json={"body": "First!"}, headers=owner_headers)
    assert r.status_code in (200, 201), r.text
    comment = r.json()
    assert comment["task_id"] == task_id
    assert comment["body"] == "First!"
    assert "id" in comment

    r = client.get(f"/tasks/{task_id}/comments", headers=owner_headers)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert any(c["body"] == "First!" for c in items)

def test_comments_forbidden_for_outsider(client):
    _register(client, "owner2@example.com")
    owner_token = _login_token(client, "owner2@example.com")
    owner_headers = _auth_headers(owner_token)
    _, _, _, task_id = _create_workspace_space_list_task(client, owner_headers)

    _register(client, "outsider@example.com")
    outsider_token = _login_token(client, "outsider@example.com")
    outsider_headers = _auth_headers(outsider_token)

    r = client.post(f"/tasks/{task_id}/comments", json={"body": "Hello"}, headers=outsider_headers)
    assert r.status_code == 403, r.text
    r = client.get(f"/tasks/{task_id}/comments", headers=outsider_headers)
    assert r.status_code == 403, r.text

def test_comments_pagination_and_edit_delete(client):
    _register(client, "author@example.com")
    token = _login_token(client, "author@example.com")
    headers = _auth_headers(token)
    _, _, _, task_id = _create_workspace_space_list_task(client, headers)

    # create 3 comments
    bodies = ["c1", "c2", "c3"]
    ids = []
    for b in bodies:
        r = client.post(f"/tasks/{task_id}/comments", json={"body": b}, headers=headers)
        assert r.status_code in (200, 201), r.text
        ids.append(r.json()["id"])

    # pagination: limit 2, offset 1
    r = client.get(f"/tasks/{task_id}/comments?limit=2&offset=1", headers=headers)
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 2

    # outsider cannot edit/delete
    _register(client, "outs@example.com")
    outsider_token = _login_token(client, "outs@example.com")
    outsider_headers = _auth_headers(outsider_token)

    r = client.put(
        f"/tasks/{task_id}/comments/{ids[0]}",
        json={"body": "edited"},
        headers=outsider_headers,
    )
    assert r.status_code == 403 or r.status_code == 404, r.text

    r = client.delete(f"/tasks/{task_id}/comments/{ids[0]}", headers=outsider_headers)
    assert r.status_code in (403, 404), r.text

    # author edits
    r = client.put(
        f"/tasks/{task_id}/comments/{ids[0]}",
        json={"body": "edited by author"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["body"] == "edited by author"

    # author deletes
    r = client.delete(f"/tasks/{task_id}/comments/{ids[0]}", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["detail"].lower().startswith("comment deleted")

    # ensure it no longer appears
    r = client.get(f"/tasks/{task_id}/comments", headers=headers)
    assert r.status_code == 200
    bodies_after = [c["body"] for c in r.json()]
    assert "edited by author" not in bodies_after
