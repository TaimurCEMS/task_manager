from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import Role, require_role

# FIX: Import 'task' from crud as well to get access to crud_task.get_task
from app.crud import core_entities as crud_core
from app.crud import custom_fields as crud_cf
from app.crud import task as crud_task
from app.db.session import get_db
from app.models.core_entities import User
from app.schemas import custom_fields as schema_cf
from app.security import get_current_user

router = APIRouter(tags=["Custom Fields"])


@router.post(
    "/workspaces/{workspace_id}/custom-fields",
    response_model=schema_cf.CustomFieldDefinitionOut,
)
def create_custom_field_definition(
    workspace_id: UUID,
    data: schema_cf.CustomFieldDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(
        db, user_id=current_user.id, workspace_id=str(workspace_id), minimum=Role.ADMIN
    )
    return crud_cf.create_definition(db, workspace_id=workspace_id, data=data)


@router.get(
    "/workspaces/{workspace_id}/custom-fields",
    response_model=List[schema_cf.CustomFieldDefinitionOut],
)
def list_custom_field_definitions(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(
        db, user_id=current_user.id, workspace_id=str(workspace_id), minimum=Role.MEMBER
    )
    return crud_cf.get_definitions_for_workspace(db, workspace_id=workspace_id)


@router.post("/lists/{list_id}/custom-fields/{field_id}/enable")
def enable_custom_field_for_list(
    list_id: UUID,
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent_list = crud_core.get_list(db, list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    require_role(
        db,
        user_id=current_user.id,
        workspace_id=space.workspace_id,
        minimum=Role.MEMBER,
    )
    crud_cf.enable_field_on_list(db, list_id=list_id, field_id=field_id)
    return {"detail": "Custom field enabled for list."}


@router.put("/tasks/{task_id}/custom-fields/{field_id}")
def set_custom_field_value(
    task_id: UUID,
    field_id: UUID,
    data: schema_cf.CustomFieldValueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # FIX: Use crud_task to get the task, not crud_core
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    parent_list = crud_core.get_list(db, task.list_id)
    space = crud_core.get_space(db, parent_list.space_id)
    require_role(
        db,
        user_id=current_user.id,
        workspace_id=space.workspace_id,
        minimum=Role.MEMBER,
    )
    crud_cf.set_value_for_task(db, task_id=task_id, field_id=field_id, value=data.value)
    return {"detail": "Custom field value updated."}
