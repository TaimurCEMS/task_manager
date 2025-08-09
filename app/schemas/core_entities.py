# File: /app/schemas/core_entities.py | Version: 2.0
from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# -------------------- Workspace --------------------

class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None


class WorkspaceOut(BaseModel):
    id: str
    name: str
    owner_id: str
    # Make timestamps optional so ResponseValidationError doesn't occur if the model lacks them
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------- Space --------------------

class SpaceCreate(BaseModel):
    name: str
    workspace_id: str


class SpaceUpdate(BaseModel):
    name: Optional[str] = None


class SpaceOut(BaseModel):
    id: str
    name: str
    workspace_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------- Folder --------------------

class FolderCreate(BaseModel):
    name: str
    space_id: str


class FolderUpdate(BaseModel):
    name: Optional[str] = None


class FolderOut(BaseModel):
    id: str
    name: str
    space_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------- List --------------------

class ListCreate(BaseModel):
    name: str
    space_id: str
    folder_id: Optional[str] = None


class ListUpdate(BaseModel):
    name: Optional[str] = None


class ListOut(BaseModel):
    id: str
    name: str
    space_id: str
    folder_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
