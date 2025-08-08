# File: app/schemas/core_entities.py | Version: 1.0 | Path: /app/schemas/core_entities.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

# Shared base for all create/update actions
class WorkspaceBase(BaseModel):
    name: str = Field(..., max_length=100)

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceUpdate(WorkspaceBase):
    pass

class WorkspaceOut(WorkspaceBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class SpaceBase(BaseModel):
    name: str = Field(..., max_length=100)
    is_private: Optional[bool] = False

class SpaceCreate(SpaceBase):
    workspace_id: UUID

class SpaceUpdate(SpaceBase):
    pass

class SpaceOut(SpaceBase):
    id: UUID
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class FolderBase(BaseModel):
    name: str = Field(..., max_length=100)

class FolderCreate(FolderBase):
    space_id: UUID

class FolderUpdate(FolderBase):
    pass

class FolderOut(FolderBase):
    id: UUID
    space_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ListBase(BaseModel):
    name: str = Field(..., max_length=100)

class ListCreate(ListBase):
    space_id: UUID
    folder_id: Optional[UUID] = None

class ListUpdate(ListBase):
    pass

class ListOut(ListBase):
    id: UUID
    space_id: UUID
    folder_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
