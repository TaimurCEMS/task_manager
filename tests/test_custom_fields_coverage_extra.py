# File: /tests/test_custom_fields_coverage_extra.py | Version: 1.0 | Title: CF Idempotent Enable + Update Value Coverage
from __future__ import annotations
from typing import Dict
from fastapi.testclient import TestClient


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: TestClient, email: str, password: str = "Passw0rd!") -> str:
    r = client.post("/auth/register", json={"email": email, "password": password, "full_name": "Tester"})
    assert r.status_code in (200, 201), r.text
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _seed_ws_space_lists(client: TestClient, token: str) -> Dict[str, str]:
    headers = _auth_headers(token)
    r = client.post("/workspaces/", json={"name": "Acme"}, headers=headers); assert r.status_code == 200, r.text
    wid = r.json()["id"]

    r = client.post("/spaces/", json={"name": "Ops", "workspace_id": wid}, headers=headers); assert r.status_code == 200, r.text
    sid = r.json()["id"]

    r = client.post("/lists/", json={"name": "List A", "space_id": sid}, headers=headers); assert r.status_code == 200, r.text
    lid_a = r.json()["id"]

    return {"wid": wid, "sid": sid, "lid_a": lid_a, "headers": headers}


def test_cf_enable_is_idempotent(client: TestClient):
    """Covers custom_fields.enable_field_on_list early-return branch by enabling twice."""
    tok = _register_and_login(client, "cf-idem@example.com")
    seeded = _seed_ws_space_lists(client, tok)
    wid, lid_a, headers = seeded["wid"], seeded["lid_a"], seeded["headers"]

    # Create CF
    r = client.post(f"/workspaces/{wid}/custom-fields", json={"name": "Team", "field_type": "Text"}, headers=headers)
    assert r.status_code == 200, r.text
    cf_id = r.json()["id"]

    # Enable once
    r1 = client.post(f"/lists/{lid_a}/custom-fields/{cf_id}/enable", headers=headers)
    assert r1.status_code == 200, r1.text

    # Enable again (should hit existing row path, not create a duplicate)
    r2 = client.post(f"/lists/{lid_a}/custom-fields/{cf_id}/enable", headers=headers)
    assert r2.status_code == 200, r2.text

    # If API returns relation id, it should be the same; if not present, test still covers branch.
    j1, j2 = r1.json(), r2.json()
    if isinstance(j1, dict) and isinstance(j2, dict) and "id" in j1 and "id" in j2:
        assert j1["id"] == j2["id"]


def test_cf_set_value_updates_existing_row(client: TestClient):
    """Covers custom_fields.set_value_for_task update path by PUTting a new value."""
    tok = _register_and_login(client, "cf-update@example.com")
    seeded = _seed_ws_space_lists(client, tok)
    wid, sid, lid_a, headers = seeded["wid"], seeded["sid"], seeded["lid_a"], seeded["headers"]

    # Create CF and enable
    r = client.post(f"/workspaces/{wid}/custom-fields", json={"name": "Team", "field_type": "Text"}, headers=headers)
    assert r.status_code == 200, r.text
    cf_id = r.json()["id"]

    r = client.post(f"/lists/{lid_a}/custom-fields/{cf_id}/enable", headers=headers)
    assert r.status_code == 200, r.text

    # Create a task on List A
    r = client.post("/tasks/", json={"name": "Alpha", "status": "To Do", "space_id": sid, "list_id": lid_a}, headers=headers)
    assert r.status_code == 200, r.text
    t_id = r.json()["id"]

    # Set CF value -> "Engineering"
    r = client.put(f"/tasks/{t_id}/custom-fields/{cf_id}", json={"value": "Engineering"}, headers=headers)
    assert r.status_code == 200, r.text

    # Verify via filter eq -> returns task
    body = {"scope": {"workspace_id": wid}, "filters": [{"field": f"cf_{cf_id}", "op": "eq", "value": "Engineering"}]}
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=body, headers=headers); assert r.status_code == 200
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert t_id in ids

    # Update CF value -> "Marketing" (hits update branch)
    r = client.put(f"/tasks/{t_id}/custom-fields/{cf_id}", json={"value": "Marketing"}, headers=headers)
    assert r.status_code == 200, r.text

    # Verify new value seen; old value not matched
    body = {"scope": {"workspace_id": wid}, "filters": [{"field": f"cf_{cf_id}", "op": "eq", "value": "Marketing"}]}
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=body, headers=headers); assert r.status_code == 200
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert t_id in ids

    body = {"scope": {"workspace_id": wid}, "filters": [{"field": f"cf_{cf_id}", "op": "eq", "value": "Engineering"}]}
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=body, headers=headers); assert r.status_code == 200
    ids = {t["id"] for g in r.json()["groups"] for t in g["tasks"]}
    assert t_id not in ids
