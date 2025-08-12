# File: /tests/test_move_subtask_api.py | Version: 1.1 | Path: /tests/test_move_subtask_api.py
from typing import Dict


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
    return r.json()["access_token"]


def _bootstrap(client, token: str):
    # Workspace from registration
    r = client.get("/workspaces/", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    ws = r.json()[0]

    # Space
    r = client.post(
        "/spaces/",
        json={"name": "S", "workspace_id": ws["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    space = r.json()

    # List A
    r = client.post(
        "/lists/",
        json={"name": "L1", "space_id": space["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    list_a = r.json()

    # List B (different list, same space)
    r = client.post(
        "/lists/",
        json={"name": "L2", "space_id": space["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    list_b = r.json()

    return ws, space, list_a, list_b


def _create_task(client, token: str, list_id: str, space_id: str, name: str):
    r = client.post(
        "/tasks/",
        json={"name": name, "list_id": list_id, "space_id": space_id},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_move_subtask_detach_and_cycle(client):
    token = _register_and_login(client, "move+owner@example.com")
    _, space, list_a, _ = _bootstrap(client, token)

    parent = _create_task(client, token, list_a["id"], space["id"], "Parent")
    # Create child as subtask under parent
    r = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={"name": "Child", "list_id": list_a["id"], "space_id": space["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    child = r.json()

    # 1) Try to move parent under its own child -> should be 400 (cycle)
    r = client.post(
        f"/tasks/{parent['id']}/move",
        json={"new_parent_task_id": child["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 400, r.text
    assert "cycle" in r.json()["detail"].lower()

    # 2) Detach the child (new_parent_task_id = null) -> OK
    r = client.post(
        f"/tasks/{child['id']}/move",
        json={"new_parent_task_id": None},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["parent_task_id"] is None

    # 3) Now move parent under the previously detached child -> OK (no cycle)
    r = client.post(
        f"/tasks/{parent['id']}/move",
        json={"new_parent_task_id": child["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["parent_task_id"] == child["id"]


def test_move_subtask_same_list_rule(client):
    token = _register_and_login(client, "move+samlist@example.com")
    _, space, list_a, list_b = _bootstrap(client, token)

    parent_a = _create_task(client, token, list_a["id"], space["id"], "Parent A")
    child = _create_task(client, token, list_a["id"], space["id"], "Child (detached)")

    # Same list: move is OK
    r = client.post(
        f"/tasks/{child['id']}/move",
        json={"new_parent_task_id": parent_a["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    moved = r.json()
    assert moved["parent_task_id"] == parent_a["id"]

    # Different list: should be 400
    parent_b = _create_task(client, token, list_b["id"], space["id"], "Parent B")
    r = client.post(
        f"/tasks/{child['id']}/move",
        json={"new_parent_task_id": parent_b["id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 400, r.text
    assert "same list" in r.json()["detail"].lower()
