# File: /tests/test_auth_refresh_extras.py | Version: 1.0 | Title: Auth refresh + /auth/me + /auth/token form
from __future__ import annotations

from typing import Dict

from fastapi.testclient import TestClient


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_refresh_and_me_and_refresh_flow(client: TestClient):
    email = "refresh@test.com"
    password = "Passw0rd!"

    # Register
    r = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Ref Tester"},
    )
    assert r.status_code in (200, 201), r.text

    # Login (JSON)
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert (
        "access_token" in body
        and "refresh_token" in body
        and body.get("token_type") == "bearer"
    )
    access_1 = body["access_token"]
    refresh = body["refresh_token"]

    # /auth/me with access token
    r = client.get("/auth/me", headers=_auth_headers(access_1))
    assert r.status_code == 200, r.text
    assert r.json().get("email") == email

    # /auth/refresh -> new access token
    r = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200, r.text
    access_2 = r.json()["access_token"]
    assert isinstance(access_2, str) and access_2
    # (likely different, but don't hard-require)
    if access_2 == access_1:
        # still valid; not a failure, but ensure string shape is non-empty
        assert len(access_2) > 10

    # Use new access token on a protected endpoint
    r = client.get("/auth/protected", headers=_auth_headers(access_2))
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True


def test_oauth_token_form_returns_both_tokens(client: TestClient):
    email = "formflow@test.com"
    password = "Passw0rd!"

    # Ensure account exists
    client.post("/auth/register", json={"email": email, "password": password})

    # OAuth2 form-style login (/auth/token)
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert (
        "access_token" in body
        and "refresh_token" in body
        and body.get("token_type") == "bearer"
    )
