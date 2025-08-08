# File: app/routers/task.py | Version: 1.2 | Path: /app/routers/task.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.schemas import task as schema
from app import crud
from app.routers.auth_dependencies import get_me
from app.core.permissions import get_user_role_for_workspace, check_permission

router = APIRouter(tags=["Tasks"])

# ----- TASK ROUTES -----

@router.post("/tasks/", response_model=schema.TaskOut)
def create_task(
    data: schema.TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Validate membership in the task's workspace via its space
    space = crud.core_entities.get_space(db, data.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    role = get_user_role_for_workspace(str(current_user.id), workspace_id=str(space.workspace_id))
    check_permission(role, ["Owner", "Admin", "Member"])
    return crud.task.create_task(db, data)

@router.get("/tasks/{task_id}", response_model=schema.TaskOut)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud.task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Verify membership using task -> space -> workspace
    space = crud.core_entities.get_space(db, task.space_id)
    role = get_user_role_for_workspace(str(current_user.id), workspace_id=str(space.workspace_id))
    if not role:
        raise HTTPException(status_code=403, detail="No access to this task")
    return task

@router.get("/tasks/by-list/{list_id}", response_model=List[schema.TaskOut])
def get_tasks_by_list(
    list_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    parent_list = crud.core_entities.get_list(db, list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud.core_entities.get_space(db, parent_list.space_id)
    role = get_user_role_for_workspace(str(current_user.id), workspace_id=str(space.workspace_id))
    if not role:
        raise HTTPException(status_code=403, detail="No access to this list")
    return crud.task.get_tasks_by_list(db, list_id)

@router.put("/tasks/{task_id}", response_model=schema.TaskOut)
def update_task(
    task_id: UUID,
    data: schema.TaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud.task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    space = crud.core_entities.get_space(db, task.space_id)
    role = get_user_role_for_workspace(str(current_user.id), workspace_id=str(space.workspace_id))
    check_permission(role, ["Owner", "Admin", "Member"])
    updated = crud.task.update_task(db, task_id, data)
    return updated

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud.task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    space = crud.core_entities.get_space(db, task.space_id)
    role = get_user_role_for_workspace(str(current_user.id), workspace_id=str(space.workspace_id))
    check_permission(role, ["Owner", "Admin"])
    deleted = crud.task.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"detail": "Task soft-deleted"}

# ----- DEPENDENCIES -----

@router.post("/tasks/dependencies/", response_model=schema.TaskDependencyOut)
def create_dependency(
    data: schema.TaskDependencyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Validate membership with the dependent task's workspace
    task = crud.task.get_task(db, data.dependent_task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Dependent task not found")
    space = crud.core_entities.get_space(db, task.space_id)
    role = get_user_role_for_workspace(str(current_user.id), workspace_id=str(space.workspace_id))
    check_permission(role, ["Owner", "Admin", "Member"])
    return crud.task.create_dependency(db, data)

@router.get("/tasks/{task_id}/dependencies", response_model=List[schema.TaskDependencyOut])
def get_dependencies(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud.task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    space = crud.core_entities.get_space(db, task.space_id)
    role = get_user_role_for_workspace(str(current_user.id), workspace_id=str(space.workspace_id))
    if not role:
        raise HTTPException(status_code=403, detail="No access to this task")
    return crud.task.get_dependencies_for_task(db, task_id)
