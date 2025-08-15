# File: /app/routers/task.py | Version: 2.2 | Title: Tasks, Subtasks, Comments Router (+assignees upsert + list search)
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.permissions import Role, get_workspace_role, has_min_role, require_role
from app.crud import comments as crud_comments
from app.crud import core_entities as crud_core
from app.crud import task as crud_task
from app.crud import watchers as crud_watchers
from app.crud.assignees import set_task_assignees
from app.db.session import get_db
from app.models.core_entities import Task, User
from app.schemas import comments as comment_schema
from app.schemas import task as schema
from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tasks"])

# =========================
# TASKS
# =========================


@router.post("/tasks/", response_model=schema.TaskOut)
def create_task(
    data: schema.TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # FIX: Add validation to ensure the parent List exists before creation.
    parent_list = crud_core.get_list(db, data.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")

    # The original space check is still valid, but can now be derived from the trusted parent_list.
    space = crud_core.get_space(db, parent_list.space_id)
    if not space:
        # This is a data integrity issue if a list exists without a space, but it's a good safeguard.
        raise HTTPException(status_code=404, detail="Parent space not found")

    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    created = crud_task.create_task(db, data)

    # persist assignees if provided
    set_task_assignees(db, task_id=str(created.id), user_ids=data.assignee_ids)

    return created


@router.get("/tasks/{task_id}", response_model=schema.TaskOut)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")
    return task


@router.get("/tasks/by-list/{list_id}", response_model=List[schema.TaskOut])
def get_tasks_by_list(
    list_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent_list = crud_core.get_list(db, list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this list")
    return crud_task.get_tasks_by_list(db, list_id)


@router.get("/tasks/by-list/{list_id}/search")
def search_tasks_by_list(
    list_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    sort: Optional[str] = Query(
        "created_at", pattern="^(created_at|due_date|priority|name|status)$"
    ),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    parent_list = crud_core.get_list(db, list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this list")

    sort_map = {
        "created_at": Task.created_at,
        "due_date": Task.due_date,
        "priority": Task.priority,
        "name": Task.name,
        "status": Task.status,
    }
    col = sort_map.get(sort or "created_at", Task.created_at)

    base = db.query(Task).filter(Task.list_id == str(list_id))
    total = (
        db.query(func.count(Task.id)).filter(Task.list_id == str(list_id)).scalar() or 0
    )
    rows = (
        base.order_by(col.desc() if order == "desc" else col.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    def _row_to_minimal_dict(t: Task) -> Dict[str, Any]:
        return {
            "id": t.id,
            "name": t.name,
            "status": getattr(t, "status", None),
            "priority": getattr(t, "priority", None),
            "due_date": getattr(t, "due_date", None),
            "list_id": str(t.list_id),
        }

    return {
        "items": [_row_to_minimal_dict(t) for t in rows],
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "order": order,
    }


@router.put("/tasks/{task_id}", response_model=schema.TaskOut)
def update_task(
    task_id: UUID,
    data: schema.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    # if the caller provided assignee_ids (including empty list), apply them
    set_task_assignees(db, task_id=str(updated.id), user_ids=data.assignee_ids)

    return updated


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        minimum=Role.ADMIN,
    )
    deleted = crud_task.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"detail": "Task deleted"}


# =========================
# DEPENDENCIES
# =========================


@router.post("/tasks/dependencies/", response_model=schema.TaskDependencyOut)
def create_dependency(
    data: schema.TaskDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@router.get(
    "/tasks/{task_id}/dependencies", response_model=List[schema.TaskDependencyOut]
)
def get_dependencies(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    if not parent_list:
        raise HTTPException(status_code=404, detail="List not found")
    space = crud_core.get_space(db, parent_list.space_id)
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")
    return crud_task.get_dependencies_for_task(db, task_id)


# =========================
# SUBTASKS
# =========================


@router.post("/tasks/{task_id}/subtasks", response_model=schema.TaskOut)
def create_subtask(
    task_id: UUID,
    data: schema.TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

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

    # persist assignees for subtask too (if provided)
    set_task_assignees(db, task_id=str(created.id), user_ids=data.assignee_ids)

    return created


@router.get("/tasks/{task_id}/subtasks", response_model=List[schema.TaskOut])
def list_subtasks(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")

    return crud_task.get_subtasks(db, task_id)


@router.post("/tasks/{task_id}/move", response_model=schema.TaskOut)
def move_subtask(
    task_id: UUID,
    body: schema.MoveSubtaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    new_parent_uuid = body.new_parent_task_id
    if new_parent_uuid is not None:
        new_parent = crud_task.get_task(db, new_parent_uuid)
        if not new_parent:
            raise HTTPException(status_code=404, detail="New parent task not found")

    try:
        moved = crud_task.move_subtask(db, task_id, new_parent_uuid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return moved


# =========================
# COMMENTS
# =========================


@router.post("/tasks/{task_id}/comments", response_model=comment_schema.CommentOut)
def create_comment(
    task_id: UUID,
    body: comment_schema.CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a comment on a task (Member+ required in the task's workspace).
    Also auto-follows the task for the commenting user (idempotent).
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

    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    created = crud_comments.create_comment(
        db, task_id=task_id, user_id=str(current_user.id), body=body.body
    )

    # best-effort follow; log on failure (avoid bare pass for Bandit B110)
    try:
        crud_watchers.follow_task(db, task_id=task_id, user_id=str(current_user.id))
    except Exception:  # noqa: BLE001
        logger.warning("follow_task failed (non-fatal)", exc_info=True)

    return created


@router.get("/tasks/{task_id}/comments", response_model=List[comment_schema.CommentOut])
def list_comments(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
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

    role = get_workspace_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this task")

    return crud_comments.get_comments_for_task(
        db, task_id=task_id, limit=limit, offset=offset
    )


@router.put(
    "/tasks/{task_id}/comments/{comment_id}", response_model=comment_schema.CommentOut
)
def update_comment(
    task_id: UUID,
    comment_id: UUID,
    body: comment_schema.CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )

    comment = crud_comments.get_comment(db, comment_id=comment_id)
    if not comment or comment.task_id != str(task_id):
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != str(current_user.id):
        raise HTTPException(
            status_code=403, detail="Only the author can edit this comment"
        )

    updated = crud_comments.update_comment(db, comment_id=comment_id, body=body.body)
    if not updated:
        raise HTTPException(status_code=404, detail="Comment not found")
    return updated


@router.delete("/tasks/{task_id}/comments/{comment_id}")
def delete_comment(
    task_id: UUID,
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    comment = crud_comments.get_comment(db, comment_id=comment_id)
    if not comment or comment.task_id != str(task_id):
        raise HTTPException(status_code=404, detail="Comment not found")

    # Use has_min_role() for cleaner, more maintainable permission check
    is_admin_plus = has_min_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.ADMIN,
    )
    if not (comment.user_id == str(current_user.id) or is_admin_plus):
        raise HTTPException(
            status_code=403, detail="Not allowed to delete this comment"
        )

    ok = crud_comments.delete_comment(db, comment_id=comment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"detail": "Comment deleted"}
