# File: /app/schemas/view.py | Version: 1.1 | Title: Pydantic v2 schema for Saved Views (ConfigDict + from_attributes)
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict

ScopeType = Literal["workspace", "space", "list"]


class ViewBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scope_type: ScopeType
    scope_id: str  # UUID as string (consistent with existing APIs)
    filters_json: Optional[Dict[str, Any]] = None
    sort_spec: Optional[str] = None  # e.g. "created_at:desc,title:asc"
    columns_json: Optional[List[str]] = None
    is_default: bool = False


class ViewCreate(ViewBase):
    pass


class ViewUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    filters_json: Optional[Dict[str, Any]] = None
    sort_spec: Optional[str] = None
    columns_json: Optional[List[str]] = None
    is_default: Optional[bool] = None


class ViewOut(ViewBase):
    id: str
    created_at: datetime

    # Pydantic v2 style
    model_config = ConfigDict(from_attributes=True)
