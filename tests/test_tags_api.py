# File: /tests/test_tags_api.py | Version: 1.0 | Path: /tests/test_tags_api.py
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

def test_tags_create_list_assign_unassign_filter(client):
    # owner
    _register(client, "owner+tags@example.com")
    token = _login_token(client, "owner+tags@example.com")
    headers = _auth_headers(token)

    workspace_id, space_id, list_id, task_id = _create_workspace_space_list_task(client, headers)

    # create two tags in workspace
    r = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "Urgent", "color": "red"}, headers=headers)
    assert r.status_code in (200, 201), r.text
    tag1 = r.json()

    r = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "Client A"}, headers=headers)
    assert r.status_code in (200, 201), r.text
    tag2 = r.json()

    # list workspace tags
    r = client.get(f"/workspaces/{workspace_id}/tags", headers=headers)
    assert r.status_code == 200, r.text
    names = [t["name"] for t in r.json()]
    assert "Urgent" in names and "Client A" in names

    # assign tag1 to the task
    r = client.post(f"/tasks/{task_id}/tags/{tag1['id']}", headers=headers)
    assert r.status_code == 200, r.text

    # list tags on task
    r = client.get(f"/tasks/{task_id}/tags", headers=headers)
    assert r.status_code == 200, r.text
    names = [t["name"] for t in r.json()]
    assert "Urgent" in names

    # filter tasks by tag
    r = client.get(f"/tags/{tag1['id']}/tasks", headers=headers)
    assert r.status_code == 200, r.text
    ids = [t["id"] for t in r.json()]
    assert task_id in ids

    # unassign
    r = client.delete(f"/tasks/{task_id}/tags/{tag1['id']}", headers=headers)
    assert r.status_code == 200, r.text

    # confirm removal
    r = client.get(f"/tasks/{task_id}/tags", headers=headers)
    assert r.status_code == 200, r.text
    names = [t["name"] for t in r.json()]
    assert "Urgent" not in names

def test_tags_permissions(client):
    # owner & outsider
    _register(client, "owner+tags2@example.com")
    owner_token = _login_token(client, "owner+tags2@example.com")
    owner_headers = _auth_headers(owner_token)

    _register(client, "outsider+tags2@example.com")
    out_token = _login_token(client, "outsider+tags2@example.com")
    out_headers = _auth_headers(out_token)

    workspace_id, space_id, list_id, task_id = _create_workspace_space_list_task(client, owner_headers)

    # owner creates a tag
    r = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "Internal"}, headers=owner_headers)
    assert r.status_code in (200, 201), r.text
    tag = r.json()

    # outsider cannot list workspace tags
    r = client.get(f"/workspaces/{workspace_id}/tags", headers=out_headers)
    assert r.status_code == 403, r.text

    # outsider cannot assign the owner's tag to the owner's task
    r = client.post(f"/tasks/{task_id}/tags/{tag['id']}", headers=out_headers)
    assert r.status_code in (403, 404), r.text
