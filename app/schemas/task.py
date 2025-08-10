from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

# ---- Base Task Schema ----

class TaskBase(BaseModel):
    # FIX: Removed the stray '.' before max_length
    name: str = Field(max_length=200)
    description: Optional[str] = None
    status: Optional[str] = "To Do"
    priority: Optional[str] = "Normal"
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    time_estimate: Optional[int] = None  # minutes
    parent_task_id: Optional[UUID] = None

class TaskCreate(TaskBase):
    list_id: UUID
    space_id: UUID
    assignee_ids: Optional[List[UUID]] = None

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    time_estimate: Optional[int] = None

class TaskOut(TaskBase):
    id: UUID
    list_id: UUID
    space_id: Optional[UUID] = None
    assignee_ids: List[UUID] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ---- Dependencies ----

class TaskDependencyCreate(BaseModel):
    task_id: UUID
    depends_on_id: UUID

class TaskDependencyOut(BaseModel):
    id: UUID
    task_id: UUID
    depends_on_id: UUID

    model_config = ConfigDict(from_attributes=True)

# ---- Move Subtask ----

class MoveSubtaskRequest(BaseModel):
    new_parent_task_id: Optional[UUID] = None
