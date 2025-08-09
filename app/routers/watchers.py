from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import core_entities as crud_core
from app.crud import task as crud_task
from app.crud import watchers as crud_watch
from app.db.session import get_db
from app.schemas import watchers as schema
from app.routers.auth_dependencies import get_me
from app.core.permissions import Role, require_role, get_workspace_role

router = APIRouter(tags=["Watchers"])

@router.get("/tasks/{task_id}/watchers", response_model=List[schema.WatcherOut])
def list_watchers(
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
    return crud_watch.get_watchers_for_task(db, task_id=task_id)

@router.post("/tasks/{task_id}/watch", response_model=schema.WatcherOut)
def follow(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    space = crud_core.get_space(db, parent_list.space_id)
    require_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id), minimum=Role.MEMBER
    )
    return crud_watch.follow_task(db, task_id=task_id, user_id=str(current_user.id))

@router.delete("/tasks/{task_id}/watch")
def unfollow(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    task = crud_task.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    parent_list = crud_core.get_list(db, task.list_id)
    space = crud_core.get_space(db, parent_list.space_id)
    require_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id), minimum=Role.MEMBER
    )
    ok = crud_watch.unfollow_task(db, task_id=task_id, user_id=str(current_user.id))
    if not ok:
        raise HTTPException(status_code=404, detail="Not watching")
    return {"detail": "Unfollowed"}
