import pytest
from typing import Dict, Any

# --- Test Helpers (can be shared in a conftest.py) ---

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

# --- Test Fixture for Setup ---

@pytest.fixture(scope="function")
def seeded_data(client):
    """
    Fixture to set up a user, workspace, space, list, and tasks
    for custom field testing. Runs once per test function.
    """
    token = _register_and_login(client, "cf-admin@example.com")
    headers = _auth_headers(token)
    
    r = client.post("/workspaces/", json={"name": "CF Test WS"}, headers=headers)
    wid = r.json()["id"]
    
    r = client.post("/spaces/", json={"name": "CF Space", "workspace_id": wid}, headers=headers)
    sid = r.json()["id"]

    r = client.post("/lists/", json={"name": "CF List", "space_id": sid}, headers=headers)
    lid = r.json()["id"]

    # Create tasks
    task1_id = client.post("/tasks/", json={"name": "Task with CF", "list_id": lid, "space_id": sid}, headers=headers).json()["id"]
    task2_id = client.post("/tasks/", json={"name": "Another Task", "list_id": lid, "space_id": sid}, headers=headers).json()["id"]
    task3_id = client.post("/tasks/", json={"name": "Task without CF value", "list_id": lid, "space_id": sid}, headers=headers).json()["id"]

    # --- Define, Enable, and Set Values all within the setup ---
    
    # 1. Define a "Team" custom field
    cf_payload = {"name": "Team", "field_type": "Dropdown"}
    r_def = client.post(f"/workspaces/{wid}/custom-fields", json=cf_payload, headers=headers)
    assert r_def.status_code == 200, r_def.text
    field_id = r_def.json()["id"]

    # 2. Enable it on the list
    r_enable = client.post(f"/lists/{lid}/custom-fields/{field_id}/enable", headers=headers)
    assert r_enable.status_code == 200, r_enable.text

    # 3. Set values on tasks
    client.put(f"/tasks/{task1_id}/custom-fields/{field_id}", json={"value": "Engineering"}, headers=headers)
    client.put(f"/tasks/{task2_id}/custom-fields/{field_id}", json={"value": "Product"}, headers=headers)

    # Return all the IDs needed for the tests
    return {
        "wid": wid, "sid": sid, "lid": lid,
        "task1_id": task1_id, "task2_id": task2_id, "task3_id": task3_id,
        "cf_team_id": field_id,
        "headers": headers
    }

# --- Custom Fields Tests ---

def test_filter_by_custom_field_value(client, seeded_data):
    """
    Tests filtering tasks using the custom field created in the setup.
    """
    wid = seeded_data["wid"]
    headers = seeded_data["headers"]
    field_id = seeded_data["cf_team_id"]
    task1_id = seeded_data["task1_id"]

    filter_payload = {
        "scope": {"workspace_id": wid},
        "filters": [
            {
                "field": f"cf_{field_id}",
                "op": "eq",
                "value": "Engineering"
            }
        ]
    }
    
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=filter_payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    
    assert body["count"] == 1
    filtered_task_id = body["groups"][0]["tasks"][0]["id"]
    assert filtered_task_id == task1_id


def test_filter_by_custom_field_is_empty(client, seeded_data):
    """
    Tests filtering for tasks where the custom field has no value set.
    """
    wid = seeded_data["wid"]
    headers = seeded_data["headers"]
    field_id = seeded_data["cf_team_id"]
    task3_id = seeded_data["task3_id"]

    filter_payload = {
        "scope": {"workspace_id": wid},
        "filters": [
            {
                "field": f"cf_{field_id}",
                "op": "is_empty"
            }
        ]
    }
    
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=filter_payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    
    assert body["count"] == 1
    filtered_task_id = body["groups"][0]["tasks"][0]["id"]
    assert filtered_task_id == task3_id
