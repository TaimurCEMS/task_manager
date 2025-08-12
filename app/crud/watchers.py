from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import core_entities as models


def follow_task(db: Session, *, task_id: UUID, user_id: str) -> models.TaskWatcher:
    existing = (
        db.query(models.TaskWatcher)
        .filter(
            models.TaskWatcher.task_id == str(task_id),
            models.TaskWatcher.user_id == user_id,
        )
        .first()
    )
    if existing:
        return existing
    w = models.TaskWatcher(task_id=str(task_id), user_id=user_id)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def unfollow_task(db: Session, *, task_id: UUID, user_id: str) -> bool:
    existing = (
        db.query(models.TaskWatcher)
        .filter(
            models.TaskWatcher.task_id == str(task_id),
            models.TaskWatcher.user_id == user_id,
        )
        .first()
    )
    if not existing:
        return False
    db.delete(existing)
    db.commit()
    return True


def get_watchers_for_task(db: Session, *, task_id: UUID) -> List[models.TaskWatcher]:
    return (
        db.query(models.TaskWatcher)
        .filter(models.TaskWatcher.task_id == str(task_id))
        .order_by(models.TaskWatcher.created_at.asc())
        .all()
    )
