# File: /tests/test_views_crud.py | Version: 2.2 | Title: Saved Views CRUD (real auth + real scope, API-only checks)
from __future__ import annotations

from typing import Dict, Any


def _login_headers(client, email: str) -> Dict[str, str]:
    client.post("/auth/register", data={"email": email, "password": "p"})
    r = client.post("/auth/token", data={"username": email, "password": "p"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _bootstrap_scope(client, headers) -> tuple[str, str, str]:
    wid = client.post("/workspaces/", json={"name": "W"}, headers=headers).json()["id"]
    sid = client.post(
        "/spaces/", json={"name": "S", "workspace_id": wid}, headers=headers
    ).json()["id"]
    lid = client.post(
        "/lists/", json={"name": "L", "space_id": sid}, headers=headers
    ).json()["id"]
    return wid, sid, lid


def test_views_crud_lifecycle(client):
    headers = _login_headers(client, "vcrud@example.com")
    _, _, lid = _bootstrap_scope(client, headers)

    # --- Create ---
    payload: Dict[str, Any] = {
        "name": "My List View",
        "scope_type": "list",
        "scope_id": lid,
        "filters_json": {"status": ["open", "in_progress"]},
        "sort_spec": "name:asc,created_at:desc",
        "columns_json": ["name", "status", "due_date"],
        "is_default": True,
    }
    r = client.post("/views", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    view_id = r.json()["id"]

    # --- List by scope (owner only) ---
    r2 = client.get(
        "/views", params={"scope_type": "list", "scope_id": lid}, headers=headers
    )
    assert r2.status_code == 200
    listing = r2.json()
    assert any(v["id"] == view_id for v in listing)

    # --- Get one ---
    r3 = client.get(f"/views/{view_id}", headers=headers)
    assert r3.status_code == 200
    assert r3.json()["name"] == "My List View"

    # --- Update ---
    r4 = client.patch(
        f"/views/{view_id}",
        json={"name": "Renamed", "is_default": False},
        headers=headers,
    )
    assert r4.status_code == 200
    assert r4.json()["name"] == "Renamed"
    assert r4.json()["is_default"] is False

    # --- Delete ---
    r5 = client.delete(f"/views/{view_id}", headers=headers)
    assert r5.status_code == 200
    assert r5.json()["detail"] == "View deleted"

    # Verify gone
    r6 = client.get(f"/views/{view_id}", headers=headers)
    assert r6.status_code == 404
