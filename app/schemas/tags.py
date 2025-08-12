# File: /app/schemas/tags.py | Version: 1.2 | Path: /app/schemas/tags.py
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TagCreate(BaseModel):
    name: str
    color: Optional[str] = None


class TagOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    color: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# -------- Bulk operations --------


class TagIdsIn(BaseModel):
    tag_ids: List[UUID]


class BulkAssignResult(BaseModel):
    assigned: int


class BulkUnassignResult(BaseModel):
    unassigned: int
