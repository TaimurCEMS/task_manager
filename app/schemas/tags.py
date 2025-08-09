# File: /app/schemas/tags.py | Version: 1.0 | Path: /app/schemas/tags.py
from __future__ import annotations

from typing import Optional
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
