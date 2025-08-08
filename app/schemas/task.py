# File: app/schemas/task.py | Version: 1.0 | Path: /app/schemas/task.py
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# ---- Base Task Schema ----

class TaskBase(BaseModel):
    name: str = Field(..., max_length=200)
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
    assignee_ids: Optional[List[UUID]] = []

class TaskUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    status: Optional[str]
    priority: Optional[str]
    due_date: Optional[datetime]
    start_date: Optional[datetime]
    time_estimate: Optional[int]

class TaskOut(TaskBase):
    id: UUID
    list_id: UUID
    space_id: UUID
    assignee_ids: List[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---- Dependency Input ----

class TaskDependencyCreate(BaseModel):
    task_id: UUID
    depends_on_id: UUID

class TaskDependencyOut(BaseModel):
    id: UUID
    task_id: UUID
    depends_on_id: UUID

    class Config:
        from_attributes = True
