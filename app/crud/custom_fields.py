# File: app/crud/custom_fields.py | Version: 1.0 | Path: app/crud/custom_fields.py
from __future__ import annotations
from typing import List, Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.custom_fields import CustomFieldDefinition, ListCustomField, CustomFieldValue
from app.schemas.custom_fields import CustomFieldDefinitionCreate

# ---- Definition CRUD ----

def create_definition(db: Session, *, workspace_id: UUID, data: CustomFieldDefinitionCreate) -> CustomFieldDefinition:
    definition = CustomFieldDefinition(
        workspace_id=str(workspace_id),
        name=data.name,
        field_type=data.field_type,
        options=data.options
    )
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return definition

def get_definitions_for_workspace(db: Session, *, workspace_id: UUID) -> List[CustomFieldDefinition]:
    return db.query(CustomFieldDefinition).filter(CustomFieldDefinition.workspace_id == str(workspace_id)).all()

# ---- Enablement CRUD ----

def enable_field_on_list(db: Session, *, list_id: UUID, field_id: UUID) -> ListCustomField:
    link = ListCustomField(list_id=str(list_id), field_definition_id=str(field_id))
    db.add(link)
    db.commit()
    db.refresh(link)
    return link

def get_enabled_fields_for_list(db: Session, *, list_id: UUID) -> List[CustomFieldDefinition]:
    return db.query(CustomFieldDefinition).join(ListCustomField).filter(ListCustomField.list_id == str(list_id)).all()

# ---- Value CRUD ----

def set_value_for_task(db: Session, *, task_id: UUID, field_id: UUID, value: Optional[Any]) -> CustomFieldValue:
    # Use merge for simplicity (upsert)
    value_obj = CustomFieldValue(
        task_id=str(task_id),
        field_definition_id=str(field_id),
        value={"value": value} # Store value in a JSON object for consistency
    )
    merged_obj = db.merge(value_obj)
    db.commit()
    return merged_obj

def get_values_for_task(db: Session, *, task_id: UUID) -> List[CustomFieldValue]:
    return db.query(CustomFieldValue).filter(CustomFieldValue.task_id == str(task_id)).all()
