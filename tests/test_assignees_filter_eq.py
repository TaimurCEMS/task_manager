# File: /tests/test_assignees_filter_eq.py | Version: 1.0 | Title: Assignee Filters E2E (eq / is_empty / is_not_empty)
from __future__ import annotations

from typing import Dict

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings


def _auth_headers(tok: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {tok}"}


def _register_and_login(client: TestClient, email: str) -> str:
    r = client.post("/auth/register", json={"email": email, "password": "Passw0rd!"})
    assert r.status_code in (200, 201), r.text
    r = client.post("/auth/login", json={"email": email, "password": "Passw0rd!"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_assignee_filters_eq_any_empty(client: TestClient):
    tok = _register_and_login(client, "assignee@test.com")
    headers = _auth_headers(tok)
    sub = jwt.decode(tok, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])["sub"]

    # seed workspace/space/list
    r = client.post("/workspaces/", json={"name": "Acme"}, headers=headers)
    assert r.status_code == 200
    wid = r.json()["id"]
    r = client.post(
        "/spaces/", json={"name": "Ops", "workspace_id": wid}, headers=headers
    )
    assert r.status_code == 200
    sid = r.json()["id"]
    r = client.post("/lists/", json={"name": "A", "space_id": sid}, headers=headers)
    assert r.status_code == 200
    lid = r.json()["id"]

    # t1 with assignee, t2 without
    r = client.post(
        "/tasks/",
        json={
            "name": "T1",
            "status": "To Do",
            "space_id": sid,
            "list_id": lid,
            "assignee_ids": [sub],
        },
        headers=headers,
    )
    assert r.status_code == 200
    t1 = r.json()["id"]
    r = client.post(
        "/tasks/",
        json={"name": "T2", "status": "To Do", "space_id": sid, "list_id": lid},
        headers=headers,
    )
    assert r.status_code == 200
    t2 = r.json()["id"]

    # eq -> t1
    r = client.post(
        f"/workspaces/{wid}/tasks/filter",
        json={
            "scope": {"workspace_id": wid},
            "filters": [{"field": "assignee_id", "op": "eq", "value": sub}],
        },
        headers=headers,
    )
    assert r.status_code == 200
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert ids == {t1}

    # is_not_empty -> t1
    r = client.post(
        f"/workspaces/{wid}/tasks/filter",
        json={
            "scope": {"workspace_id": wid},
            "filters": [{"field": "assignee_id", "op": "is_not_empty"}],
        },
        headers=headers,
    )
    assert r.status_code == 200
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert ids == {t1}

    # is_empty -> t2
    r = client.post(
        f"/workspaces/{wid}/tasks/filter",
        json={
            "scope": {"workspace_id": wid},
            "filters": [{"field": "assignee_id", "op": "is_empty"}],
        },
        headers=headers,
    )
    assert r.status_code == 200
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert ids == {t2}
