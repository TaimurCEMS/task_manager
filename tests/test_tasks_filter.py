# File: /tests/test_tasks_filter.py | Version: 2.0 (Updated)
"""
Tests for the unified filtering & grouping feature.
- Includes fast unit tests for schemas and pure functions.
- Includes DB-backed integration tests for the live endpoint to ensure
  end-to-end functionality, including permissions, scoping, and grouping.
"""
from __future__ import annotations

import pytest
from typing import Dict, Any, List, Tuple

try:
    from app.routers.tasks_filter import router as _router
except ImportError:
    pytest.skip("tasks_filter router not present/ready; skipping.", allow_module_level=True)

from fastapi import HTTPException

# Schemas / CRUD helpers under test
from app.schemas.filters import (
    FilterPayload, FilterRule, FilterOperator, TaskField, Scope,
    TagsFilter, TagsMatch, GroupBy
)
from app.crud.filtering import group_tasks
from app.routers.tasks_filter import filter_tasks

# =====================================================================
# Test Helpers (shared between unit and integration tests)
# =====================================================================

class _TaskStub:
    """A minimal task-like object for grouping unit tests (no DB required)."""
    def __init__(self, id, name, status=None, priority=None, due_date=None, start_date=None, list_id=None, assignee_id=None):
        self.id, self.name, self.status, self.priority, self.due_date, self.start_date, self.list_id, self.assignee_id = \
            id, name, status, priority, due_date, start_date, list_id, assignee_id

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
# Section 1: Unit Tests (No Database Interaction)
# =====================================================================

def test_scope_requires_one_identifier():
    with pytest.raises(ValueError):
        Scope()

def test_filter_rule_variants_construct():
    FilterRule(field=TaskField.status, op=FilterOperator.eq, value="open")
    FilterRule(field=TaskField.priority, op=FilterOperator.in_, value=["high", "urgent"])
    FilterRule(field=TaskField.name, op=FilterOperator.contains, value="login")
    FilterRule(field=TaskField.start_date, op=FilterOperator.is_empty)
    # No exception means schema accepts these forms

def test_group_tasks_by_status_handles_no_value():
    tasks = [
        _TaskStub(id="t1", name="A", status="Open"),
        _TaskStub(id="t2", name="B", status=None),
        _TaskStub(id="t3", name="C", status="Done"),
    ]
    groups = group_tasks(tasks, group_by="status")
    gmap = {g["group"]: [t["id"] for t in g["tasks"]] for g in groups}
    assert "Open" in gmap and "Done" in gmap and "No Value" in gmap
    assert gmap["No Value"] == ["t2"]

def test_group_tasks_default_single_bucket_when_no_groupby():
    tasks = [_TaskStub(id="t1", name="A"), _TaskStub(id="t2", name="B")]
    groups = group_tasks(tasks, group_by=None)
    assert len(groups) == 1
    assert groups[0]["group"] is None
    assert {t["id"] for t in groups[0]["tasks"]} == {"t1", "t2"}

# =====================================================================
# Section 2: Integration Tests (Database Interaction)
# =====================================================================

@pytest.fixture(scope="module")
def seeded_data(client):
    """Fixture to set up all necessary data for the filter tests once per module."""
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

    # Create Tags
    tag1_id = client.post(f"/workspaces/{wid}/tags", json={"name": "Urgent", "color": "red"}, headers=headers).json()["id"]
    tag2_id = client.post(f"/workspaces/{wid}/tags", json={"name": "Backend"}, headers=headers).json()["id"]

    # Create Tasks
    task1_id = client.post("/tasks/", json={"name": "Fix login bug", "list_id": lid_a, "space_id": sid, "status": "In Progress", "priority": "High"}, headers=headers).json()["id"]
    task2_id = client.post("/tasks/", json={"name": "Develop API endpoint", "list_id": lid_a, "space_id": sid, "status": "To Do", "priority": "High"}, headers=headers).json()["id"]
    task3_id = client.post("/tasks/", json={"name": "Deploy to staging", "list_id": lid_b, "space_id": sid, "status": "In Progress", "priority": "Normal"}, headers=headers).json()["id"]
    
    # Assign tags: Task 1 -> Urgent, Backend; Task 2 -> Backend
    client.post(f"/tasks/{task1_id}/tags:assign", json={"tag_ids": [tag1_id, tag2_id]}, headers=headers)
    client.post(f"/tasks/{task2_id}/tags:assign", json={"tag_ids": [tag2_id]}, headers=headers)

    data = {
        "wid": wid, "sid": sid, "lid_a": lid_a, "lid_b": lid_b,
        "task1_id": task1_id, "task2_id": task2_id, "task3_id": task3_id,
        "tag1_id": tag1_id, "tag2_id": tag2_id, "headers": headers
    }
    return data

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
    
    groups = {group["group"]: [task["id"] for task in group["tasks"]] for group in body["groups"]}
    
    assert "In Progress" in groups and "To Do" in groups
    assert set(groups["In Progress"]) == {seeded_data["task1_id"], seeded_data["task3_id"]}
    assert groups["To Do"] == [seeded_data["task2_id"]]

def test_filter_permissions_for_outsider(client, seeded_data):
    """Ensure an unauthorized user cannot access the filter endpoint."""
    outsider_token = _register_and_login(client, "outsider-filter@example.com")
    outsider_headers = _auth_headers(outsider_token)
    
    payload = {"scope": {"workspace_id": seeded_data["wid"]}}
    r = client.post(f"/workspaces/{seeded_data['wid']}/tasks/filter", json=payload, headers=outsider_headers)
    
    assert r.status_code == 403
