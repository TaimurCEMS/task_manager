# File: /app/crud/assignees.py | Version: 1.0 | Title: Task Assignees Upsert Helper
from __future__ import annotations

from typing import Iterable, Optional
from sqlalchemy.orm import Session

from app.models.core_entities import TaskAssignee


def set_task_assignees(
    db: Session,
    *,
    task_id: str,
    user_ids: Optional[Iterable[str]],
) -> None:
    """
    Idempotently replace assignees for a task.
    - If user_ids is None: do nothing (caller didn't intend to change assignees).
    - If user_ids is []: clear all assignees.
    - Else: delete existing and insert the given user_ids (deduped).
    """
    if user_ids is None:
        return

    # Clear existing
    db.query(TaskAssignee).filter(TaskAssignee.task_id == str(task_id)).delete()

    # Insert new (if any)
    new_ids = {str(u) for u in user_ids if u}
    for uid in new_ids:
        db.add(TaskAssignee(task_id=str(task_id), user_id=str(uid)))

    db.commit()
