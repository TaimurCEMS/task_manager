# File: /tests/test_tags_api.py | Version: 1.2 | Path: /tests/test_tags_api.py
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

    # filter tasks by tag (single-tag endpoint)
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

def test_filter_tasks_by_multiple_tags_any_all(client):
    _register(client, "owner+multitags@example.com")
    token = _login_token(client, "owner+multitags@example.com")
    headers = _auth_headers(token)
    workspace_id, space_id, list_id, task1_id = _create_workspace_space_list_task(client, headers)

    # second task in same list/space
    r = client.post("/tasks/", json={"name": "T2", "space_id": space_id, "list_id": list_id}, headers=headers)
    assert r.status_code in (200, 201), r.text
    task2_id = r.json()["id"]

    # tags
    r = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "Bug"}, headers=headers); tag_bug = r.json()
    r = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "High"}, headers=headers); tag_high = r.json()
    r = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "Backend"}, headers=headers); tag_be = r.json()

    # assign: task1 -> Bug+High ; task2 -> High only
    assert client.post(f"/tasks/{task1_id}/tags/{tag_bug['id']}", headers=headers).status_code == 200
    assert client.post(f"/tasks/{task1_id}/tags/{tag_high['id']}", headers=headers).status_code == 200
    assert client.post(f"/tasks/{task2_id}/tags/{tag_high['id']}", headers=headers).status_code == 200

    # ANY: should return both tasks when filtering by [Bug, High]
    url_any = f"/workspaces/{workspace_id}/tasks/by-tags?tag_ids={tag_bug['id']}&tag_ids={tag_high['id']}&match=any"
    r = client.get(url_any, headers=headers); assert r.status_code == 200, r.text
    got_any = {t["id"] for t in r.json()}
    assert {task1_id, task2_id}.issubset(got_any)

    # ALL: should return only task1 (has both Bug and High)
    url_all = f"/workspaces/{workspace_id}/tasks/by-tags?tag_ids={tag_bug['id']}&tag_ids={tag_high['id']}&match=all"
    r = client.get(url_all, headers=headers); assert r.status_code == 200, r.text
    got_all = [t["id"] for t in r.json()]
    assert got_all == [task1_id]

def test_bulk_assign_unassign(client):
    _register(client, "owner+bulk@example.com")
    token = _login_token(client, "owner+bulk@example.com")
    headers = _auth_headers(token)
    workspace_id, space_id, list_id, task_id = _create_workspace_space_list_task(client, headers)

    # make 3 tags
    t1 = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "Design"}, headers=headers).json()
    t2 = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "API"}, headers=headers).json()
    t3 = client.post(f"/workspaces/{workspace_id}/tags", json={"name": "Low"}, headers=headers).json()

    # bulk assign two
    r = client.post(f"/tasks/{task_id}/tags:assign", json={"tag_ids": [t1["id"], t2["id"]]}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["assigned"] >= 2

    # bulk unassign one
    r = client.post(f"/tasks/{task_id}/tags:unassign", json={"tag_ids": [t1["id"]]}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["unassigned"] >= 1

    # verify state
    names = [t["name"] for t in client.get(f"/tasks/{task_id}/tags", headers=headers).json()]
    assert "API" in names and "Design" not in names
