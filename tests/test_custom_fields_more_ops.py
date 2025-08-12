from typing import Dict

import pytest


# Local helpers (match existing test style)
def _register_and_login(client, email: str, password: str = "pass123") -> str:
    client.post("/auth/register", json={"email": email, "password": password})
    r = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return r.json()["access_token"]


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def seeded_data(client):
    """
    Set up: user -> workspace -> space -> list -> three tasks
    Define a custom field and set values on two tasks.
    """
    token = _register_and_login(client, "cf-more@example.com")
    headers = _auth_headers(token)

    wid = client.post("/workspaces/", json={"name": "WS"}, headers=headers).json()["id"]
    sid = client.post(
        "/spaces/", json={"name": "SP", "workspace_id": wid}, headers=headers
    ).json()["id"]
    lid = client.post(
        "/lists/", json={"name": "L", "space_id": sid}, headers=headers
    ).json()["id"]

    t1 = client.post(
        "/tasks/",
        json={"name": "Alpha", "list_id": lid, "space_id": sid},
        headers=headers,
    ).json()["id"]
    t2 = client.post(
        "/tasks/",
        json={"name": "Beta", "list_id": lid, "space_id": sid},
        headers=headers,
    ).json()["id"]
    t3 = client.post(
        "/tasks/",
        json={"name": "Gamma", "list_id": lid, "space_id": sid},
        headers=headers,
    ).json()["id"]

    # Create CF definition, enable on list, set values on 2/3 tasks
    cf_def = client.post(
        f"/workspaces/{wid}/custom-fields",
        json={"name": "Team", "field_type": "Dropdown"},
        headers=headers,
    )
    assert cf_def.status_code == 200, cf_def.text
    field_id = cf_def.json()["id"]

    en = client.post(f"/lists/{lid}/custom-fields/{field_id}/enable", headers=headers)
    assert en.status_code == 200, en.text

    client.put(
        f"/tasks/{t1}/custom-fields/{field_id}",
        json={"value": "Engineering"},
        headers=headers,
    )
    client.put(
        f"/tasks/{t2}/custom-fields/{field_id}",
        json={"value": "Product"},
        headers=headers,
    )
    # t3 deliberately left without a CF value

    return {
        "wid": wid,
        "sid": sid,
        "lid": lid,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "cf_id": field_id,
        "headers": headers,
    }


def _filter(client, wid, headers, payload):
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    ids = [task["id"] for g in body["groups"] for task in g["tasks"]]
    return body, ids


def test_cf_contains(client, seeded_data):
    wid, headers, fid = seeded_data["wid"], seeded_data["headers"], seeded_data["cf_id"]
    body, ids = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "filters": [{"field": f"cf_{fid}", "op": "contains", "value": "gineer"}],
        },
    )
    assert body["count"] == 1
    assert ids == [seeded_data["t1"]]


def test_cf_in_and_not_in(client, seeded_data):
    wid, headers, fid = seeded_data["wid"], seeded_data["headers"], seeded_data["cf_id"]

    # IN: should match both Engineering and Product
    _, ids_in = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "filters": [
                {"field": f"cf_{fid}", "op": "in", "value": ["Engineering", "Product"]}
            ],
        },
    )
    assert set(ids_in) == {seeded_data["t1"], seeded_data["t2"]}

    # NOT IN: exclude "Product"; tasks with no CF value are not included in NOT IN branch
    _, ids_not_in = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "filters": [{"field": f"cf_{fid}", "op": "not_in", "value": ["Product"]}],
        },
    )
    assert set(ids_not_in) == {seeded_data["t1"]}


def test_cf_is_not_empty(client, seeded_data):
    wid, headers, fid = seeded_data["wid"], seeded_data["headers"], seeded_data["cf_id"]
    body, ids = _filter(
        client,
        wid,
        headers,
        {
            "scope": {"workspace_id": wid},
            "filters": [{"field": f"cf_{fid}", "op": "is_not_empty"}],
        },
    )
    assert body["count"] == 2
    assert set(ids) == {seeded_data["t1"], seeded_data["t2"]}


def test_group_by_custom_field(client, seeded_data):
    wid, headers, fid = seeded_data["wid"], seeded_data["headers"], seeded_data["cf_id"]
    r = client.post(
        f"/workspaces/{wid}/tasks/filter",
        json={"scope": {"workspace_id": wid}, "group_by": f"cf_{fid}"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    groups = {g["group"]: [t["id"] for t in g["tasks"]] for g in body["groups"]}
    assert "Engineering" in groups and "Product" in groups and "No Value" in groups
    assert set(groups["Engineering"]) == {seeded_data["t1"]}
    assert set(groups["Product"]) == {seeded_data["t2"]}
    assert set(groups["No Value"]) == {seeded_data["t3"]}
