from typing import Any, Dict, List


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


def _filter(
    client, wid: str, headers: Dict[str, str], payload: Dict[str, Any]
) -> List[str]:
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    return [task["id"] for group in body["groups"] for task in group["tasks"]]


def test_ordering_and_pagination(client):
    """
    Verify default ordering (created_at DESC) and limit/offset behavior in the filter endpoint.
    The query orders by Task.created_at DESC with limit/offset:contentReference[oaicite:18]{index=18}.
    """
    token = _register_and_login(client, "pager@example.com")
    headers = _auth_headers(token)

    wid = client.post("/workspaces/", json={"name": "PW"}, headers=headers).json()["id"]
    sid = client.post(
        "/spaces/", json={"name": "PS", "workspace_id": wid}, headers=headers
    ).json()["id"]
    lid = client.post(
        "/lists/", json={"name": "PL", "space_id": sid}, headers=headers
    ).json()["id"]

    # Create 3 tasks in known order: t1 (oldest) -> t2 -> t3 (newest)
    t1 = client.post(
        "/tasks/", json={"name": "T1", "list_id": lid, "space_id": sid}, headers=headers
    ).json()["id"]
    t2 = client.post(
        "/tasks/", json={"name": "T2", "list_id": lid, "space_id": sid}, headers=headers
    ).json()["id"]
    t3 = client.post(
        "/tasks/", json={"name": "T3", "list_id": lid, "space_id": sid}, headers=headers
    ).json()["id"]

    # No filters, default page (limit default from schema), check first page starts with newest (t3, t2, t1)
    ids_all = _filter(
        client, wid, headers, {"scope": {"workspace_id": wid}, "filters": []}
    )
    assert ids_all[:3] == [t3, t2, t1]

    # limit=2 -> should return [t3, t2]
    ids_page1 = _filter(
        client,
        wid,
        headers,
        {"scope": {"workspace_id": wid}, "filters": [], "limit": 2, "offset": 0},
    )
    assert ids_page1 == [t3, t2]

    # limit=1, offset=1 -> second item i.e., t2
    ids_page2 = _filter(
        client,
        wid,
        headers,
        {"scope": {"workspace_id": wid}, "filters": [], "limit": 1, "offset": 1},
    )
    assert ids_page2 == [t2]
