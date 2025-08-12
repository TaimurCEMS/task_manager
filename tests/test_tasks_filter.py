# File: /tests/test_tasks_filter.py | Version: 1.0 | Title: End-to-End Filters (Scope, Tags, Custom Fields, Grouping)
from __future__ import annotations

from typing import Dict, List

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
    token = r.json()["access_token"]
    return token


def _seed_basics(client: TestClient, token: str) -> Dict[str, str]:
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
    def _make_task(name: str, status: str, list_id: str) -> str:
        payload = {"name": name, "status": status, "list_id": list_id, "space_id": sid}
        r2 = client.post("/tasks/", json=payload, headers=headers)
        assert r2.status_code == 200, r2.text
        return r2.json()["id"]

    t1 = _make_task("Alpha", "In Progress", lid_a)
    t2 = _make_task("Bravo", "To Do", lid_a)
    t3 = _make_task("Charlie", "In Progress", lid_b)

    # Tags
    r = client.post(f"/workspaces/{wid}/tags", json={"name": "Red"}, headers=headers)
    assert r.status_code == 200, r.text
    red_id = r.json()["id"]

    r = client.post(f"/workspaces/{wid}/tags", json={"name": "Blue"}, headers=headers)
    assert r.status_code == 200, r.text
    blue_id = r.json()["id"]

    # Assign tags: t1 -> [Red, Blue], t2 -> [Red]
    r = client.post(
        f"/tasks/{t1}/tags:assign", json={"tag_ids": [red_id, blue_id]}, headers=headers
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/tasks/{t2}/tags:assign", json={"tag_ids": [red_id]}, headers=headers
    )
    assert r.status_code == 200, r.text

    # Custom Field (workspace)
    r = client.post(
        f"/workspaces/{wid}/custom-fields",
        json={"name": "Team", "field_type": "Text"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    cf_id = r.json()["id"]

    # Enable CF on List A only
    r = client.post(f"/lists/{lid_a}/custom-fields/{cf_id}/enable", headers=headers)
    assert r.status_code == 200, r.text

    # Set CF values for t1, t2 (t3 is intentionally left empty)
    r = client.put(
        f"/tasks/{t1}/custom-fields/{cf_id}",
        json={"value": "Engineering"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    r = client.put(
        f"/tasks/{t2}/custom-fields/{cf_id}",
        json={"value": "Marketing"},
        headers=headers,
    )
    assert r.status_code == 200, r.text

    return {
        "wid": wid,
        "sid": sid,
        "lid_a": lid_a,
        "lid_b": lid_b,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "red_id": red_id,
        "blue_id": blue_id,
        "cf_id": cf_id,
        "headers": headers,
    }


def _filter(client: TestClient, wid: str, headers: Dict[str, str], payload: dict):
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _ids_from_groups(body: dict) -> List[str]:
    ids: List[str] = []
    for g in body["groups"]:
        ids += [t["id"] for t in g["tasks"]]
    return ids


def test_filter_by_status_eq(client: TestClient):
    token = _register_and_login(client, "alice@example.com")
    seeded = _seed_basics(client, token)
    wid, headers = seeded["wid"], seeded["headers"]

    body = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "filters": [{"field": "status", "op": "eq", "value": "In Progress"}],
        },
    )
    ids = set(_ids_from_groups(body))
    assert body["count"] == 2
    assert ids == {seeded["t1"], seeded["t3"]}


def test_filter_tags_any_vs_all(client: TestClient):
    token = _register_and_login(client, "bob@example.com")
    seeded = _seed_basics(client, token)
    wid, headers = seeded["wid"], seeded["headers"]

    # ANY (Red)
    body = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "tags": {"tag_ids": [seeded["red_id"]], "match": "any"},
        },
    )
    assert set(_ids_from_groups(body)) == {seeded["t1"], seeded["t2"]}

    # ALL (Red + Blue) -> only t1
    body = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "tags": {"tag_ids": [seeded["red_id"], seeded["blue_id"]], "match": "all"},
        },
    )
    assert set(_ids_from_groups(body)) == {seeded["t1"]}


def test_filter_by_custom_field_eq_and_is_empty(client: TestClient):
    token = _register_and_login(client, "carol@example.com")
    seeded = _seed_basics(client, token)
    wid, headers, cf_id = seeded["wid"], seeded["headers"], seeded["cf_id"]

    # CF eq Engineering -> t1
    body = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "filters": [{"field": f"cf_{cf_id}", "op": "eq", "value": "Engineering"}],
        },
    )
    assert set(_ids_from_groups(body)) == {seeded["t1"]}

    # CF is_empty (t3 has no value; also list B not enabled)
    body = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "filters": [{"field": f"cf_{cf_id}", "op": "is_empty"}],
        },
    )
    assert seeded["t3"] in set(_ids_from_groups(body))


def test_scope_list_and_group_by_status(client: TestClient):
    token = _register_and_login(client, "dana@example.com")
    seeded = _seed_basics(client, token)
    wid, headers = seeded["wid"], seeded["headers"]

    # Scope: List B only (should contain t3)
    body = _filter(
        client,
        wid,
        headers,
        {"scope": {"list_id": seeded["lid_b"]}, "filters": [], "group_by": "status"},
    )
    ids = set(_ids_from_groups(body))
    assert ids == {seeded["t3"]}
    # Group names should include "In Progress"
    groups = {g["group"] for g in body["groups"]}
    assert "In Progress" in groups


def test_filter_permissions_for_outsider(client: TestClient):
    # Owner creates data
    owner_token = _register_and_login(client, "owner@example.com")
    seeded = _seed_basics(client, owner_token)
    wid = seeded["wid"]

    # Outsider tries to filter same workspace
    outsider_token = _register_and_login(client, "outsider@example.com")
    headers = _auth_headers(outsider_token)

    r = client.post(
        f"/workspaces/{wid}/tasks/filter",
        json={"scope": {"workspace_id": wid}, "filters": []},
        headers=headers,
    )
    assert r.status_code in (401, 403)
