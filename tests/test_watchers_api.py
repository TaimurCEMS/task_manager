from typing import Dict, Tuple


def _register(
    client, email: str, password: str = "Passw0rd!", full_name: str = "Test User"
):
    r = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def _login_token(client, email: str, password: str = "Passw0rd!") -> str:
    r = client.post(
        "/auth/token",
        data={"username": email, "password": password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code == 200 and "access_token" in r.json():
        return r.json()["access_token"]
    r = client.post("/auth/login", json={"username": email, "password": password})
    assert r.status_code == 200 and "access_token" in r.json(), r.text
    return r.json()["access_token"]


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _bootstrap(client, headers) -> Tuple[str, str, str, str]:
    r = client.post("/workspaces/", json={"name": "W"}, headers=headers)
    wid = r.json()["id"]
    r = client.post(
        "/spaces/", json={"name": "S", "workspace_id": wid}, headers=headers
    )
    sid = r.json()["id"]
    r = client.post("/lists/", json={"name": "L", "space_id": sid}, headers=headers)
    lid = r.json()["id"]
    r = client.post(
        "/tasks/", json={"name": "T1", "list_id": lid, "space_id": sid}, headers=headers
    )
    tid = r.json()["id"]
    return wid, sid, lid, tid


def test_watch_follow_unfollow_and_list(client):
    _register(client, "owner+watch@example.com")
    token = _login_token(client, "owner+watch@example.com")
    headers = _auth_headers(token)
    wid, sid, lid, tid = _bootstrap(client, headers)

    # initially empty
    r = client.get(f"/tasks/{tid}/watchers", headers=headers)
    assert r.status_code == 200 and r.json() == [], r.text

    # follow -> listed once
    r = client.post(f"/tasks/{tid}/watch", headers=headers)
    assert r.status_code == 200, r.text
    r = client.get(f"/tasks/{tid}/watchers", headers=headers)
    users = [w["user_id"] for w in r.json()]
    assert len(users) == 1

    # idempotent follow
    r = client.post(f"/tasks/{tid}/watch", headers=headers)
    assert r.status_code == 200, r.text
    r = client.get(f"/tasks/{tid}/watchers", headers=headers)
    users = [w["user_id"] for w in r.json()]
    assert len(users) == 1

    # unfollow
    r = client.delete(f"/tasks/{tid}/watch", headers=headers)
    assert r.status_code == 200, r.text
    r = client.get(f"/tasks/{tid}/watchers", headers=headers)
    assert r.json() == []


def test_watch_permissions(client):
    _register(client, "owner+watch2@example.com")
    token_owner = _login_token(client, "owner+watch2@example.com")
    h_owner = _auth_headers(token_owner)

    _register(client, "outsider+watch2@example.com")
    token_out = _login_token(client, "outsider+watch2@example.com")
    h_out = _auth_headers(token_out)

    wid, sid, lid, tid = _bootstrap(client, h_owner)

    # outsider cannot view watchers (no workspace membership)
    r = client.get(f"/tasks/{tid}/watchers", headers=h_out)
    assert r.status_code == 403, r.text

    # outsider cannot follow/unfollow
    assert client.post(f"/tasks/{tid}/watch", headers=h_out).status_code == 403
    assert client.delete(f"/tasks/{tid}/watch", headers=h_out).status_code in (403, 404)
