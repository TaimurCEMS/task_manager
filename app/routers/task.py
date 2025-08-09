# File: /app/routers/task.py | Version: 1.7 | Path: /app/routers/task.py
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import core_entities as crud_core
from app.crud import task as crud_task
from app.crud import comments as crud_comments
from app.db.session import get_db
from app.schemas import task as schema
from app.schemas import comments as comment_schema
from app.routers.auth_dependencies import get_me
from app.core.permissions import Role, require_role, get_workspace_role

router = APIRouter(tags=["Tasks"])

# ----- TASK ROUTES -----

@router.post("/tasks/", response_model=schema.TaskOut)
def create_task(
    data: schema.TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Validate membership in the task's workspace via its space
    space = crud_core.get_space(db, data.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )
    return crud_task.create_task(db, data)


@router.get("/tasks/{task_id}", response_model=schema.TaskOut)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Verify membership using task -> list -> space -> workspace
    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    role = get_workspace_role(db, user_id=str(current_user.id), workspace_id=str(space.workspace_id))
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")
    return task


@router.get("/tasks/by-list/{list_id}", response_model=List[schema.TaskOut])
def get_tasks_by_list(
    list_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    parent_list = crud_core.get_list(db, list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    role = get_workspace_role(db, user_id=str(current_user.id), workspace_id=str(space.workspace_id))
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this list")
    return crud_task.get_tasks_by_list(db, list_id)


@router.put("/tasks/{task_id}", response_model=schema.TaskOut)
def update_task(
    task_id: UUID,
    data: schema.TaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )
    updated = crud_task.update_task(db, task_id, data)
    return updated


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    # Admin+ can delete
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.ADMIN,
    )
    deleted = crud_task.delete_task(db, task_id)
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
    task = crud_task.get_task(db, data.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )
    return crud_task.create_dependency(db, data)


@router.get("/tasks/{task_id}/dependencies", response_model=List[schema.TaskDependencyOut])
def get_dependencies(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    role = get_workspace_role(db, user_id=str(current_user.id), workspace_id=str(space.workspace_id))
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")
    return crud_task.get_dependencies_for_task(db, task_id)


# ----- SUBTASKS -----

@router.post("/tasks/{task_id}/subtasks", response_model=schema.TaskOut)
def create_subtask(
    task_id: UUID,
    data: schema.TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    """
    Create a subtask under the given parent task.
    NOTE: We enforce that the subtask uses the same list as the parent.
          Any list_id/space_id sent by the client is ignored.
    """
    parent = crud_task.get_task(db, task_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent task not found")

    parent_list = crud_core.get_list(db, parent.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="Parent list not found")

    space = crud_core.get_space(db, parent_list.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Permission: Member+ in the parent task's workspace
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    # Build payload that forces same-list rule
    payload = schema.TaskCreate(
        list_id=UUID(parent.list_id),
        space_id=UUID(space.id),
        name=data.name,
        description=data.description,
        status=data.status,
        priority=data.priority,
        due_date=data.due_date,
        start_date=data.start_date,
        time_estimate=data.time_estimate,
        assignee_ids=data.assignee_ids,
        parent_task_id=task_id,
    )
    created = crud_task.create_subtask(db, task_id, payload)
    return created


@router.get("/tasks/{task_id}/subtasks", response_model=List[schema.TaskOut])
def list_subtasks(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    parent = crud_task.get_task(db, task_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent task not found")

    parent_list = crud_core.get_list(db, parent.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="Parent list not found")

    space = crud_core.get_space(db, parent_list.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Permission: Member+ in the parent task's workspace (view requires membership)
    role = get_workspace_role(db, user_id=str(current_user.id), workspace_id=str(space.workspace_id))
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")

    return crud_task.get_subtasks(db, task_id)


@router.post("/tasks/{task_id}/move", response_model=schema.TaskOut)
def move_subtask(
    task_id: UUID,
    body: schema.MoveSubtaskRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    """
    Move a task under a new parent, or detach by passing null.
    Enforces membership in the task's workspace; prevents cycles; requires same list.
    """
    # Task being moved
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Resolve workspace for permission check via current parent list -> space -> workspace
    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Permission: Member+ in the workspace
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    # If provided, ensure the new parent exists (so we can return 404 vs 400)
    new_parent_uuid = body.new_parent_task_id
    if new_parent_uuid is not None:
        new_parent = crud_task.get_task(db, new_parent_uuid)
        if not new_parent:
            raise HTTPException(status_code=404, detail="New parent task not found")

    # Execute the move
    try:
        moved = crud_task.move_subtask(db, task_id, new_parent_uuid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return moved


# ----- COMMENTS (NEW) -----

@router.post("/tasks/{task_id}/comments", response_model=comment_schema.CommentOut)
def create_comment(
    task_id: UUID,
    body: comment_schema.CommentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    """
    Create a comment on a task (Member+ required in the task's workspace).
    """
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Permission: Member+ in workspace
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    created = crud_comments.create_comment(
        db, task_id=task_id, user_id=str(current_user.id), body=body.body
    )
    return created


@router.get("/tasks/{task_id}/comments", response_model=List[comment_schema.CommentOut])
def list_comments(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # View permission: any member of the workspace
    role = get_workspace_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")

    return crud_comments.get_comments_for_task(db, task_id=task_id)
