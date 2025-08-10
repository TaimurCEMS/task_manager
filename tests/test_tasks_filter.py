import pytest
from typing import Dict, Any, List, Tuple

# FIX: Removed all direct imports from the deleted 'app.crud.filtering' file.
# The tests now only interact with the live API, which is a more robust testing strategy.

# =====================================================================
# Test Helpers
# =====================================================================

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

# =====================================================================
# Integration Tests (Database Interaction)
# =====================================================================

@pytest.fixture(scope="function")
def seeded_data(client):
    """Sets up a user, workspace, lists, tags, and tasks for filter tests."""
    token = _register_and_login(client, "filter-user@example.com")
    headers = _auth_headers(token)
    
    r = client.post("/workspaces/", json={"name": "Filter Test WS"}, headers=headers)
    wid = r.json()["id"]
    
    r = client.post("/spaces/", json={"name": "Filter Test Space", "workspace_id": wid}, headers=headers)
    sid = r.json()["id"]

    r = client.post("/lists/", json={"name": "List A", "space_id": sid}, headers=headers)
    lid_a = r.json()["id"]
    
    r = client.post("/lists/", json={"name": "List B", "space_id": sid}, headers=headers)
    lid_b = r.json()["id"]

    tag1_id = client.post(f"/workspaces/{wid}/tags", json={"name": "Urgent", "color": "red"}, headers=headers).json()["id"]
    tag2_id = client.post(f"/workspaces/{wid}/tags", json={"name": "Backend"}, headers=headers).json()["id"]

    task1_id = client.post("/tasks/", json={"name": "Fix login bug", "list_id": lid_a, "space_id": sid, "status": "In Progress", "priority": "High"}, headers=headers).json()["id"]
    task2_id = client.post("/tasks/", json={"name": "Develop API endpoint", "list_id": lid_a, "space_id": sid, "status": "To Do", "priority": "High"}, headers=headers).json()["id"]
    task3_id = client.post("/tasks/", json={"name": "Deploy to staging", "list_id": lid_b, "space_id": sid, "status": "In Progress", "priority": "Normal"}, headers=headers).json()["id"]
    
    client.post(f"/tasks/{task1_id}/tags:assign", json={"tag_ids": [tag1_id, tag2_id]}, headers=headers)
    client.post(f"/tasks/{task2_id}/tags:assign", json={"tag_ids": [tag2_id]}, headers=headers)

    return {
        "wid": wid, "sid": sid, "lid_a": lid_a, "lid_b": lid_b,
        "task1_id": task1_id, "task2_id": task2_id, "task3_id": task3_id,
        "tag1_id": tag1_id, "tag2_id": tag2_id, "headers": headers
    }

def _filter_request(client, headers: Dict[str, str], wid: str, payload: Dict[str, Any]) -> Tuple[int, List[str]]:
    """Helper to make a filter request and return the count and a list of task IDs."""
    r = client.post(f"/workspaces/{wid}/tasks/filter", json=payload, headers=headers)
    assert r.status_code == 200, f"Filter request failed: {r.text}"
    body = r.json()
    task_ids = [task["id"] for group in body["groups"] for task in group["tasks"]]
    return body["count"], task_ids

def test_filter_by_status(client, seeded_data):
    """Verify filtering by a single standard attribute (status)."""
    payload = {
        "scope": {"workspace_id": seeded_data["wid"]},
        "filters": [{"field": "status", "op": "eq", "value": "In Progress"}]
    }
    count, ids = _filter_request(client, seeded_data["headers"], seeded_data["wid"], payload)
    assert count == 2
    assert set(ids) == {seeded_data["task1_id"], seeded_data["task3_id"]}

def test_filter_by_multiple_attributes(client, seeded_data):
    """Verify filtering by a combination of attributes (priority AND status)."""
    payload = {
        "scope": {"workspace_id": seeded_data["wid"]},
        "filters": [
            {"field": "priority", "op": "eq", "value": "High"},
            {"field": "status", "op": "eq", "value": "To Do"}
        ]
    }
    count, ids = _filter_request(client, seeded_data["headers"], seeded_data["wid"], payload)
    assert count == 1
    assert ids[0] == seeded_data["task2_id"]

def test_filter_by_tags_all(client, seeded_data):
    """Verify filtering for tasks that have ALL of the specified tags."""
    payload = {
        "scope": {"workspace_id": seeded_data["wid"]},
        "tags": {"tag_ids": [seeded_data["tag1_id"], seeded_data["tag2_id"]], "match": "all"}
    }
    count, ids = _filter_request(client, seeded_data["headers"], seeded_data["wid"], payload)
    assert count == 1
    assert ids[0] == seeded_data["task1_id"]

def test_filter_with_list_scope(client, seeded_data):
    """Verify that scoping the filter to a specific list works correctly."""
    payload = {
        "scope": {"list_id": seeded_data["lid_b"]},
        "filters": []
    }
    count, ids = _filter_request(client, seeded_data["headers"], seeded_data["wid"], payload)
    assert count == 1
    assert ids[0] == seeded_data["task3_id"]

def test_grouping_by_status(client, seeded_data):
    """Verify that the grouping feature correctly buckets tasks by status."""
    payload = {
        "scope": {"workspace_id": seeded_data["wid"]},
        "group_by": "status"
    }
    r = client.post(f"/workspaces/{seeded_data['wid']}/tasks/filter", json=payload, headers=seeded_data["headers"])
    assert r.status_code == 200
    body = r.json()
    
    groups = {group["group"]: {task["id"] for task in group["tasks"]} for group in body["groups"]}
    
    assert "In Progress" in groups
    assert "To Do" in groups
    assert groups["In Progress"] == {seeded_data["task1_id"], seeded_data["task3_id"]}
    assert groups["To Do"] == {seeded_data["task2_id"]}

def test_filter_permissions_for_outsider(client, seeded_data):
    """Ensure an unauthorized user cannot access the filter endpoint."""
    outsider_token = _register_and_login(client, "outsider-filter@example.com")
    outsider_headers = _auth_headers(outsider_token)
    
    payload = {"scope": {"workspace_id": seeded_data["wid"]}}
    r = client.post(f"/workspaces/{seeded_data['wid']}/tasks/filter", json=payload, headers=outsider_headers)
    
    assert r.status_code == 403
