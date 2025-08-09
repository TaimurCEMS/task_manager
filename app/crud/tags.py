from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
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


# -------- Multi-tag filtering (workspace-scoped) --------

def get_tasks_by_tags(
    db: Session,
    *,
    workspace_id: UUID,
    tag_ids: List[UUID],
    match: str = "any",
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[models.Task]:
    """
    Return tasks in a workspace that match multiple tags.
    match='any' -> task has at least one of the tags
    match='all' -> task has all of the tags
    """
    if not tag_ids:
        return []

    tag_id_strs = [str(t) for t in tag_ids]

    q = (
        db.query(models.Task)
        .join(models.List, models.Task.list_id == models.List.id)
        .join(models.Space, models.List.space_id == models.Space.id)
        .filter(models.Space.workspace_id == str(workspace_id))
        .join(models.TaskTag, models.TaskTag.task_id == models.Task.id)
        .filter(models.TaskTag.tag_id.in_(tag_id_strs))
    )

    if match == "all":
        q = (
            q.group_by(models.Task.id)
            .having(func.count(func.distinct(models.TaskTag.tag_id)) == len(tag_id_strs))
        )
    else:  # 'any' (DB-agnostic; avoid DISTINCT ON)
        q = q.group_by(models.Task.id)

    q = q.order_by(models.Task.created_at.desc())

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)

    return q.all()
