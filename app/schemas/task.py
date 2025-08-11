# File: /app/schemas/task.py | Version: 1.0 | Title: Task Schemas (Pydantic v2, BaseSchema)
from __future__ import annotations
from typing import Optional, List
from uuid import UUID

from app.schemas._base import BaseSchema


# ---- Core Task payloads ----

class TaskCreate(BaseSchema):
    list_id: UUID
    space_id: UUID
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    time_estimate: Optional[int] = None
    assignee_ids: Optional[List[str]] = None
    parent_task_id: Optional[UUID] = None


class TaskUpdate(BaseSchema):
    # All fields optional for PATCH-like updates
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    time_estimate: Optional[int] = None
    assignee_ids: Optional[List[str]] = None
    parent_task_id: Optional[UUID] = None
    list_id: Optional[UUID] = None  # allow moving tasks between lists


class TaskOut(BaseSchema):
    # Use str for IDs to play nice with ORM/String PKs
    id: str
    list_id: str
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    time_estimate: Optional[int] = None
    parent_task_id: Optional[str] = None


# ---- Dependencies ----

class TaskDependencyCreate(BaseSchema):
    task_id: UUID
    depends_on_task_id: UUID
    type: Optional[str] = None  # e.g., "blocks", "relates"


class TaskDependencyOut(BaseSchema):
    id: str
    task_id: str
    depends_on_task_id: str
    type: Optional[str] = None


# ---- Subtask helpers ----

class MoveSubtaskRequest(BaseSchema):
    new_parent_task_id: Optional[UUID] = None
