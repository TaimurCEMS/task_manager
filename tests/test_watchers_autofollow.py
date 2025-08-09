from typing import Dict, Tuple

def _register(client, email: str, password: str = "Passw0rd!", full_name: str = "Test User"):
    r = client.post("/auth/register", json={"email": email, "password": password, "full_name": full_name})
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
    r = client.post("/workspaces/", json={"name": "W"}, headers=headers); wid = r.json()["id"]
    r = client.post("/spaces/", json={"name": "S", "workspace_id": wid}, headers=headers); sid = r.json()["id"]
    r = client.post("/lists/", json={"name": "L", "space_id": sid}, headers=headers); lid = r.json()["id"]
    r = client.post("/tasks/", json={"name": "T1", "list_id": lid, "space_id": sid}, headers=headers); tid = r.json()["id"]
    return wid, sid, lid, tid

def test_comment_auto_adds_watcher(client):
    _register(client, "owner+auto@example.com")
    token = _login_token(client, "owner+auto@example.com")
    headers = _auth_headers(token)
    wid, sid, lid, tid = _bootstrap(client, headers)

    # initially no watchers
    r = client.get(f"/tasks/{tid}/watchers", headers=headers)
    assert r.status_code == 200 and r.json() == [], r.text

    # add a comment
    r = client.post(f"/tasks/{tid}/comments", json={"body": "hello"}, headers=headers)
    assert r.status_code in (200, 201), r.text

    # now we're a watcher (exactly one)
    r = client.get(f"/tasks/{tid}/watchers", headers=headers)
    users = [w["user_id"] for w in r.json()]
    assert len(users) == 1
