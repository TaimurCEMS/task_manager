# File: /tests/test_phase5_coverage_bump.py | Version: 1.0 | Title: Extra Coverage for Permissions & Filters
from __future__ import annotations

from typing import Dict
from uuid import uuid4

from fastapi.testclient import TestClient


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


def _seed_minimal(client: TestClient, token: str):
    headers = _auth_headers(token)
    # Workspace
    r = client.post("/workspaces/", json={"name": "Acme"}, headers=headers)
    assert r.status_code == 200, r.text
    wid = r.json()["id"]
    # Space
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

    # Tasks
    def mk(name, status, priority, list_id):
        payload = {
            "name": name,
            "status": status,
            "priority": priority,
            "list_id": list_id,
            "space_id": sid,
        }
        r2 = client.post("/tasks/", json=payload, headers=headers)
        assert r2.status_code == 200, r2.text
        return r2.json()["id"]

    t1 = mk("Alpha", "In Progress", "High", lid_a)
    t2 = mk("Bravo", "To Do", "Low", lid_a)
    t3 = mk("Charlie", "In Progress", "", lid_b)  # no priority, covers "No Value" group
    return {
        "wid": wid,
        "sid": sid,
        "lid_a": lid_a,
        "lid_b": lid_b,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "headers": headers,
    }


def test_auth_invalid_token_401(client: TestClient):
    r = client.get(
        "/auth/protected",
        headers={"Authorization": "Bearer definitely-not-a-valid-token"},
    )
    assert r.status_code == 401


def test_task_get_and_delete_404(client: TestClient):
    bogus = str(uuid4())
    r = client.get(f"/tasks/{bogus}")
    assert (
        r.status_code == 401 or r.status_code == 404
    )  # unauth or not found both cover code paths

    token = _register_and_login(client, "noone@example.com")
    headers = _auth_headers(token)
    r = client.delete(f"/tasks/{bogus}", headers=headers)
    assert r.status_code == 404  # router.delete returns 404 for non-existent


def test_task_update_outsider_403(client: TestClient):
    owner_tok = _register_and_login(client, "owner2@example.com")
    seeded = _seed_minimal(client, owner_tok)
    outsider_tok = _register_and_login(client, "outsider2@example.com")
    r = client.put(
        f"/tasks/{seeded['t1']}",
        json={"name": "Evil rename"},
        headers=_auth_headers(outsider_tok),
    )
    assert r.status_code in (401, 403)  # must not be allowed


def test_filters_cf_ops_and_grouping(client: TestClient):
    tok = _register_and_login(client, "cf-cov@example.com")
    seeded = _seed_minimal(client, tok)
    wid, headers = seeded["wid"], seeded["headers"]

    # Create + enable CF
    r = client.post(
        f"/workspaces/{wid}/custom-fields",
        json={"name": "Team", "field_type": "Text"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    cf_id = r.json()["id"]

    r = client.post(
        f"/lists/{seeded['lid_a']}/custom-fields/{cf_id}/enable", headers=headers
    )
    assert r.status_code == 200, r.text

    # Set CF values for two tasks (third remains empty)
    r = client.put(
        f"/tasks/{seeded['t1']}/custom-fields/{cf_id}",
        json={"value": "Engineering"},
        headers=headers,
    )
    assert r.status_code == 200
    r = client.put(
        f"/tasks/{seeded['t2']}/custom-fields/{cf_id}",
        json={"value": "Marketing"},
        headers=headers,
    )
    assert r.status_code == 200

    # NE -> should find Marketing (t2)
    body = {
        "scope": {"workspace_id": wid},
        "filters": [{"field": f"cf_{cf_id}", "op": "ne", "value": "Engineering"}],
    }
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=body, headers=headers)
    assert r.status_code == 200, r.text
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert seeded["t2"] in ids

    # NOT IN -> exclude Engineering -> should return Marketing (t2)
    body = {
        "scope": {"workspace_id": wid},
        "filters": [{"field": f"cf_{cf_id}", "op": "not_in", "value": ["Engineering"]}],
    }
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=body, headers=headers)
    assert r.status_code == 200
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert seeded["t2"] in ids and seeded["t1"] not in ids

    # IS NOT EMPTY -> should include t1 and t2, exclude t3
    body = {
        "scope": {"workspace_id": wid},
        "filters": [{"field": f"cf_{cf_id}", "op": "is_not_empty"}],
    }
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=body, headers=headers)
    assert r.status_code == 200
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert seeded["t1"] in ids and seeded["t2"] in ids and seeded["t3"] not in ids

    # Group by native priority -> expect "High", "Low", and "No Value" groups
    body = {"scope": {"workspace_id": wid}, "group_by": "priority"}
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=body, headers=headers)
    assert r.status_code == 200
    groups = {g["group"] for g in r.json()["groups"]}
    assert "High" in groups and "Low" in groups and "No Value" in groups
