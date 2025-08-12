# File: /tests/test_cov_phase5_plus.py | Version: 1.1 | Title: Coverage: admin delete, move-subtask error, CF contains/in/group-by
from __future__ import annotations

from typing import Dict
from uuid import uuid4

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(
    client: TestClient, email: str, password: str = "Passw0rd!"
) -> str:
    r = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Tester"},
    )
    assert r.status_code in (200, 201), r.text
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _seed(client: TestClient, token: str):
    headers = _auth_headers(token)

    # decode user id from JWT (sub)
    user_id = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])[
        "sub"
    ]

    # Workspace + Space
    r = client.post("/workspaces/", json={"name": "Acme"}, headers=headers)
    assert r.status_code == 200, r.text
    wid = r.json()["id"]

    r = client.post(
        "/spaces/", json={"name": "Ops", "workspace_id": wid}, headers=headers
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    # Lists
    r = client.post(
        "/lists/", json={"name": "List A", "space_id": sid}, headers=headers
    )
    assert r.status_code == 200, r.text
    lid_a = r.json()["id"]
    r = client.post(
        "/lists/", json={"name": "List B", "space_id": sid}, headers=headers
    )
    assert r.status_code == 200, r.text
    lid_b = r.json()["id"]

    # Tasks (no reliance on assignees)
    def mk(name, status, list_id):
        payload = {"name": name, "status": status, "list_id": list_id, "space_id": sid}
        r2 = client.post("/tasks/", json=payload, headers=headers)
        assert r2.status_code == 200, r2.text
        return r2.json()["id"]

    t1 = mk("Alpha", "In Progress", lid_a)
    t2 = mk("Bravo", "To Do", lid_a)
    t3 = mk("Charlie", "In Progress", lid_b)

    # Custom field: create + enable on List A
    r = client.post(
        f"/workspaces/{wid}/custom-fields",
        json={"name": "Team", "field_type": "Text"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    cf_id = r.json()["id"]

    r = client.post(f"/lists/{lid_a}/custom-fields/{cf_id}/enable", headers=headers)
    assert r.status_code == 200, r.text

    # Set CF values for A-list tasks only; leave List B without value
    r = client.put(
        f"/tasks/{t1}/custom-fields/{cf_id}",
        json={"value": "Engineering"},
        headers=headers,
    )
    assert r.status_code == 200
    r = client.put(
        f"/tasks/{t2}/custom-fields/{cf_id}",
        json={"value": "Marketing"},
        headers=headers,
    )
    assert r.status_code == 200

    return {
        "wid": wid,
        "sid": sid,
        "lid_a": lid_a,
        "lid_b": lid_b,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "headers": headers,
        "user_id": user_id,
        "cf_id": cf_id,
    }


def _ids(body: dict):
    return {t["id"] for g in body["groups"] for t in g["tasks"]}


def test_admin_delete_and_move_subtask_invalid_parent(client: TestClient):
    tok = _register_and_login(client, "admin-del@example.com")
    s = _seed(client, tok)
    _, headers = s["wid"], s["headers"]

    # Admin (owner) can delete t2
    r = client.delete(f"/tasks/{s['t2']}", headers=headers)
    assert r.status_code == 200, r.text

    # Move subtask with bogus new_parent -> should 404 "New parent task not found"
    r = client.post(
        f"/tasks/{s['t1']}/move",
        json={"new_parent_task_id": str(uuid4())},
        headers=headers,
    )
    assert r.status_code == 404, r.text


def test_cf_contains_in_and_group_by_cf(client: TestClient):
    tok = _register_and_login(client, "cf-cov2@example.com")
    s = _seed(client, tok)
    wid, headers, cf = s["wid"], s["headers"], s["cf_id"]

    # contains (case-insensitive): "engine" -> t1
    r = client.post(
        f"/workspaces/{wid}/tasks/filter",
        json={
            "scope": {"workspace_id": wid},
            "filters": [{"field": f"cf_{cf}", "op": "contains", "value": "engine"}],
        },
        headers=headers,
    )
    assert r.status_code == 200
    assert s["t1"] in _ids(r.json())

    # in_ -> Engineering or Sales -> t1 only
    r = client.post(
        f"/workspaces/{wid}/tasks/filter",
        json={
            "scope": {"workspace_id": wid},
            "filters": [
                {"field": f"cf_{cf}", "op": "in", "value": ["Engineering", "Sales"]}
            ],
        },
        headers=headers,
    )
    assert r.status_code == 200
    ids = _ids(r.json())
    assert s["t1"] in ids and s["t2"] not in ids

    # group by custom field -> expect "Engineering", "Marketing", "No Value"
    r = client.post(
        f"/workspaces/{wid}/tasks/filter",
        json={"scope": {"workspace_id": wid}, "group_by": f"cf_{cf}"},
        headers=headers,
    )
    assert r.status_code == 200
    groups = {g["group"] for g in r.json()["groups"]}
    assert {"Engineering", "Marketing", "No Value"} <= groups
