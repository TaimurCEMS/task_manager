# File: /tests/test_router_smoke.py | Version: 1.0 | Path: /tests/test_router_smoke.py
def test_openapi_has_core_task_routes(client):
    # Ask FastAPI for its OpenAPI schema and verify key routes exist
    r = client.get("/openapi.json")
    assert r.status_code == 200, r.text
    paths = r.json().get("paths", {})

    expected = {
        "/tasks/": ["post"],
        "/tasks/{task_id}": ["get", "put", "delete"],
        "/tasks/by-list/{list_id}": ["get"],
        "/tasks/dependencies/": ["post"],
        "/tasks/{task_id}/dependencies": ["get"],
        "/tasks/{task_id}/subtasks": ["get", "post"],
        "/tasks/{task_id}/move": ["post"],
        "/tasks/{task_id}/comments": ["get", "post"],
    }

    missing = []
    for p, methods in expected.items():
        if p not in paths:
            missing.append(f"{p} (missing path)")
            continue
        present = {m.lower() for m in paths[p].keys()}
        for m in methods:
            if m not in present:
                missing.append(f"{p} missing {m.upper()}")

    assert not missing, "Missing routes: " + ", ".join(missing)
