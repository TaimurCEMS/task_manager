# File: /app/routers/tags.py | Version: 1.0 | Path: /app/routers/tags.py
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import core_entities as crud_core
from app.crud import task as crud_task
from app.crud import tags as crud_tags
from app.db.session import get_db
from app.schemas import tags as tag_schema
from app.schemas import task as task_schema
from app.routers.auth_dependencies import get_me
from app.core.permissions import Role, require_role, get_workspace_role

router = APIRouter(tags=["Tags"])

# ---------- Workspace-level tags ----------

@router.post("/workspaces/{workspace_id}/tags", response_model=tag_schema.TagOut)
def create_tag(
    workspace_id: UUID,
    data: tag_schema.TagCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # permissions: Member+ of workspace can create/list tags
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(workspace_id),
        minimum=Role.MEMBER,
    )
    # ensure workspace exists (404 vs silent create)
    ws = crud_core.get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    created = crud_tags.create_tag(db, workspace_id=workspace_id, name=data.name, color=data.color)
    return created


@router.get("/workspaces/{workspace_id}/tags", response_model=List[tag_schema.TagOut])
def list_workspace_tags(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    role = get_workspace_role(db, user_id=str(current_user.id), workspace_id=str(workspace_id))
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this workspace")
    return crud_tags.get_workspace_tags(db, workspace_id=workspace_id)

# ---------- Task ↔ tag ----------

@router.get("/tasks/{task_id}/tags", response_model=List[tag_schema.TagOut])
def list_task_tags(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    space = crud_core.get_space(db, parent_list.space_id)
    role = get_workspace_role(db, user_id=str(current_user.id), workspace_id=str(space.workspace_id))
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")
    return crud_tags.get_tags_for_task(db, task_id=task_id)


@router.post("/tasks/{task_id}/tags/{tag_id}")
def assign_tag(
    task_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # task/workspace membership
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    space = crud_core.get_space(db, parent_list.space_id)
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    # tag exists and matches same workspace
    tag = crud_tags.get_tag(db, tag_id=tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.workspace_id != str(space.workspace_id):
        raise HTTPException(status_code=400, detail="Tag workspace mismatch with task")

    crud_tags.assign_tag_to_task(db, task_id=task_id, tag_id=tag_id)
    return {"detail": "Tag assigned"}


@router.delete("/tasks/{task_id}/tags/{tag_id}")
def unassign_tag(
    task_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    space = crud_core.get_space(db, parent_list.space_id)
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    tag = crud_tags.get_tag(db, tag_id=tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.workspace_id != str(space.workspace_id):
        raise HTTPException(status_code=400, detail="Tag workspace mismatch with task")

    crud_tags.unassign_tag_from_task(db, task_id=task_id, tag_id=tag_id)
    return {"detail": "Tag unassigned"}

# ---------- Filter by tag ----------

@router.get("/tags/{tag_id}/tasks", response_model=List[task_schema.TaskOut])
def list_tasks_for_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    tag = crud_tags.get_tag(db, tag_id=tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # membership in the tag's workspace
    role = get_workspace_role(db, user_id=str(current_user.id), workspace_id=tag.workspace_id)
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this workspace")

    return crud_tags.get_tasks_for_tag(db, tag_id=tag_id)
