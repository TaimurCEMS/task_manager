# File: tests/test_protected.py | Version: 1.0 | Path: /tests/test_protected.py
from fastapi.testclient import TestClient

def _login(client: TestClient) -> str:
    # assumes you already have a user from the auth test; if not, register quickly
    client.post("/auth/register", json={"email": "p2@example.com", "password": "secret123"})
    resp = client.post(
        "/auth/login",
        data={"username": "p2@example.com", "password": "secret123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_protected_endpoint(client: TestClient):
    token = _login(client)
    r = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (200, 204)  # adjust based on your endpoint
