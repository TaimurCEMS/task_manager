# File: /app/crud/tags.py | Version: 1.3 | Path: /app/crud/tags.py
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, delete
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


def get_tags_by_ids(db: Session, *, tag_ids: List[UUID]) -> List[models.Tag]:
    if not tag_ids:
        return []
    ids = [str(t) for t in tag_ids]
    return list(db.query(models.Tag).filter(models.Tag.id.in_(ids)).all())


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


def assign_tags_to_task(db: Session, *, task_id: UUID, tag_ids: List[UUID]) -> int:
    """Bulk-assign; returns number of new links created."""
    if not tag_ids:
        return 0
    ids = [str(t) for t in tag_ids]

    existing_ids = {
        row.tag_id
        for row in db.query(models.TaskTag).filter(
            models.TaskTag.task_id == str(task_id),
            models.TaskTag.tag_id.in_(ids),
        )
    }
    to_create = [tid for tid in ids if tid not in existing_ids]
    if not to_create:
        return 0

    links = [models.TaskTag(task_id=str(task_id), tag_id=tid) for tid in to_create]
    db.add_all(links)
    db.commit()
    return len(links)


def unassign_tags_from_task(db: Session, *, task_id: UUID, tag_ids: List[UUID]) -> int:
    """Bulk-unassign; returns number of links removed."""
    if not tag_ids:
        return 0
    ids = [str(t) for t in tag_ids]
    stmt = (
        delete(models.TaskTag)
        .where(models.TaskTag.task_id == str(task_id))
        .where(models.TaskTag.tag_id.in_(ids))
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


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
    else:  # 'any'
        q = q.group_by(models.Task.id)

    q = q.order_by(models.Task.created_at.desc())

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)

    return q.all()
