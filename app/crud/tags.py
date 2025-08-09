# File: /app/crud/tags.py | Version: 1.0 | Path: /app/crud/tags.py
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import core_entities as models


# -------- Tags (workspace-scoped) --------

def create_tag(db: Session, *, workspace_id: UUID, name: str, color: Optional[str]) -> models.Tag:
    tag = models.Tag(workspace_id=str(workspace_id), name=name, color=color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_workspace_tags(db: Session, *, workspace_id: UUID) -> List[models.Tag]:
    return (
        db.query(models.Tag)
        .filter(models.Tag.workspace_id == str(workspace_id))
        .order_by(models.Tag.name.asc())
        .all()
    )


def get_tag(db: Session, *, tag_id: UUID | str) -> Optional[models.Tag]:
    return db.get(models.Tag, str(tag_id))


# -------- Task ↔ Tag assignment --------

def get_tags_for_task(db: Session, *, task_id: UUID) -> List[models.Tag]:
    return (
        db.query(models.Tag)
        .join(models.TaskTag, models.TaskTag.tag_id == models.Tag.id)
        .filter(models.TaskTag.task_id == str(task_id))
        .order_by(models.Tag.name.asc())
        .all()
    )


def assign_tag_to_task(db: Session, *, task_id: UUID, tag_id: UUID) -> bool:
    existing = (
        db.query(models.TaskTag)
        .filter(
            models.TaskTag.task_id == str(task_id),
            models.TaskTag.tag_id == str(tag_id),
        )
        .first()
    )
    if existing:
        return False
    link = models.TaskTag(task_id=str(task_id), tag_id=str(tag_id))
    db.add(link)
    db.commit()
    return True


def unassign_tag_from_task(db: Session, *, task_id: UUID, tag_id: UUID) -> bool:
    link = (
        db.query(models.TaskTag)
        .filter(
            models.TaskTag.task_id == str(task_id),
            models.TaskTag.tag_id == str(tag_id),
        )
        .first()
    )
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True


def get_tasks_for_tag(db: Session, *, tag_id: UUID) -> List[models.Task]:
    return (
        db.query(models.Task)
        .join(models.TaskTag, models.TaskTag.task_id == models.Task.id)
        .filter(models.TaskTag.tag_id == str(tag_id))
        .order_by(models.Task.created_at.desc())
        .all()
    )
