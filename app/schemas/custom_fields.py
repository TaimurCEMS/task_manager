from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---- Custom Field Definition ----


class CustomFieldDefinitionCreate(BaseModel):
    # FIX: Removed the stray '.' before max_length
    name: str = Field(max_length=100)
    field_type: str  # e.g. 'Text', 'Number', 'Dropdown'
    options: Optional[Dict[str, Any]] = None


class CustomFieldDefinitionOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    field_type: str
    options: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# ---- Custom Field Value ----


class CustomFieldValueUpdate(BaseModel):
    value: Optional[Any] = None


class CustomFieldValueOut(BaseModel):
    field_definition_id: UUID
    name: str
    field_type: str
    value: Optional[Any] = None


# ---- API Specific Schemas ----


class TaskWithCustomFieldsOut(BaseModel):
    id: UUID
    name: str
    # ... other task fields
    custom_fields: List[CustomFieldValueOut] = []

    model_config = ConfigDict(from_attributes=True)
