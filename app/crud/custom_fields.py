# File: /app/crud/custom_fields.py | Version: 1.1 | Title: Custom Fields CRUD (robust imports)
from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

# Try modern split-module layout first, then fallback to monolith core_entities
try:
    from app.models.custom_fields import (
        CustomFieldDefinition,
        CustomFieldValue,
        ListCustomField,
    )
except ImportError:  # fallback if your project keeps them in core_entities
    from app.models.core_entities import (
        CustomFieldDefinition,
        CustomFieldValue,
        ListCustomField,
    )


# ---- Definitions ----


def create_definition(
    db: Session,
    *,
    workspace_id: UUID | str,
    data,
) -> CustomFieldDefinition:
    """
    data: schemas.custom_fields.CustomFieldDefinitionCreate
    """
    obj = CustomFieldDefinition(
        workspace_id=str(workspace_id),
        name=data.name,
        field_type=data.field_type,
        options=data.options or None,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_definitions_for_workspace(
    db: Session, *, workspace_id: UUID | str
) -> List[CustomFieldDefinition]:
    return (
        db.query(CustomFieldDefinition)
        .filter(CustomFieldDefinition.workspace_id == str(workspace_id))
        .order_by(CustomFieldDefinition.name.asc())
        .all()
    )


# ---- Enable on List ----


def enable_field_on_list(
    db: Session, *, list_id: UUID | str, field_id: UUID | str
) -> ListCustomField:
    existing = (
        db.query(ListCustomField)
        .filter(
            ListCustomField.list_id == str(list_id),
            ListCustomField.field_definition_id == str(field_id),
        )
        .first()
    )
    if existing:
        return existing
    rel = ListCustomField(list_id=str(list_id), field_definition_id=str(field_id))
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


# ---- Task Value (Upsert) ----


def set_value_for_task(
    db: Session, *, task_id: UUID | str, field_id: UUID | str, value: Any
) -> CustomFieldValue:
    """
    Values are stored as JSON: {"value": <raw>} so they can be typed/fetched consistently.
    """
    row: Optional[CustomFieldValue] = (
        db.query(CustomFieldValue)
        .filter(
            CustomFieldValue.task_id == str(task_id),
            CustomFieldValue.field_definition_id == str(field_id),
        )
        .first()
    )
    if row:
        row.value = {"value": value}
        db.commit()
        db.refresh(row)
        return row

    row = CustomFieldValue(
        task_id=str(task_id),
        field_definition_id=str(field_id),
        value={"value": value},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
