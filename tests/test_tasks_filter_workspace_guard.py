import uuid
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


def test_workspace_scope_guard_mismatch_returns_400(client):
    """
    The filter router rejects a payload whose scope.workspace_id does not match the path workspace_id.
    """
    token = _register_and_login(client, "guard@test.com")
    headers = _auth_headers(token)

    wid = client.post("/workspaces/", json={"name": "WG"}, headers=headers).json()["id"]
    sid = client.post(
        "/spaces/", json={"name": "S", "workspace_id": wid}, headers=headers
    ).json()["id"]
    lid = client.post(
        "/lists/", json={"name": "L", "space_id": sid}, headers=headers
    ).json()["id"]
    client.post(
        "/tasks/", json={"name": "T", "list_id": lid, "space_id": sid}, headers=headers
    )

    # Use a different (random) workspace_id in the payload than the path — router must 400
    # Guard exists in tasks_filter router:contentReference[oaicite:10]{index=10} with path prefix /workspaces.
    other_wid = str(uuid.uuid4())
    payload = {"scope": {"workspace_id": other_wid}, "filters": []}
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=payload, headers=headers)
    assert r.status_code == 400, r.text
