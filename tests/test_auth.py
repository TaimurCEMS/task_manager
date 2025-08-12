# File: tests/test_auth.py | Version: 1.1 | Path: /tests/test_auth.py
from fastapi.testclient import TestClient


def test_register_and_login(client: TestClient):
    # Adjust payload keys/routes if your API expects different names
    reg = client.post(
        "/auth/register", json={"email": "test@example.com", "password": "secret123"}
    )
    assert reg.status_code in (200, 201)

    login = client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "secret123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    data = login.json()
    assert "access_token" in data
    assert data.get("token_type") in ("bearer", "Bearer")
