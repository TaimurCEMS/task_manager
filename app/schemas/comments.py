# File: /app/schemas/comments.py | Version: 1.1 | Path: /app/schemas/comments.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CommentCreate(BaseModel):
    body: str


class CommentUpdate(BaseModel):
    body: str


class CommentOut(BaseModel):
    id: str
    task_id: str
    user_id: str
    body: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
