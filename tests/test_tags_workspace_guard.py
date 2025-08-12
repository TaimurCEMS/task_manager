from typing import Dict


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


def test_cannot_assign_tag_from_other_workspace(client):
    """
    Assigning a tag that belongs to a different workspace to a task must 400.
    The tags router enforces 'Tag workspace mismatch with task'.
    """
    token = _register_and_login(client, "tags-guard@example.com")
    headers = _auth_headers(token)

    # Workspace A + task
    wa = client.post("/workspaces/", json={"name": "WA"}, headers=headers).json()["id"]
    sa = client.post(
        "/spaces/", json={"name": "SA", "workspace_id": wa}, headers=headers
    ).json()["id"]
    la = client.post(
        "/lists/", json={"name": "LA", "space_id": sa}, headers=headers
    ).json()["id"]
    task_a = client.post(
        "/tasks/", json={"name": "T", "list_id": la, "space_id": sa}, headers=headers
    ).json()["id"]

    # Workspace B + tag
    wb = client.post("/workspaces/", json={"name": "WB"}, headers=headers).json()["id"]
    tb = client.post(
        f"/workspaces/{wb}/tags", json={"name": "Other"}, headers=headers
    ).json()

    # Try to assign tag from WB to task in WA -> 400
    r = client.post(f"/tasks/{task_a}/tags/{tb['id']}", headers=headers)
    assert r.status_code == 400, r.text


def test_bulk_assign_mismatch_any_tag_400(client):
    token = _register_and_login(client, "tags-guard2@example.com")
    headers = _auth_headers(token)

    # Workspace A + task
    wa = client.post("/workspaces/", json={"name": "WA2"}, headers=headers).json()["id"]
    sa = client.post(
        "/spaces/", json={"name": "SA2", "workspace_id": wa}, headers=headers
    ).json()["id"]
    la = client.post(
        "/lists/", json={"name": "LA2", "space_id": sa}, headers=headers
    ).json()["id"]
    task_a = client.post(
        "/tasks/", json={"name": "TA2", "list_id": la, "space_id": sa}, headers=headers
    ).json()["id"]

    # Workspace A tag + Workspace B tag
    ta_ok = client.post(
        f"/workspaces/{wa}/tags", json={"name": "OK"}, headers=headers
    ).json()
    wb = client.post("/workspaces/", json={"name": "WB2"}, headers=headers).json()["id"]
    tb_bad = client.post(
        f"/workspaces/{wb}/tags", json={"name": "BAD"}, headers=headers
    ).json()

    # Bulk assign with one mismatched tag -> 400 per router check
    r = client.post(
        f"/tasks/{task_a}/tags:assign",
        json={"tag_ids": [ta_ok["id"], tb_bad["id"]]},
        headers=headers,
    )
    assert r.status_code == 400, r.text
