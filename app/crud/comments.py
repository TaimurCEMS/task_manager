# File: /app/crud/comments.py | Version: 1.2 | Path: /app/crud/comments.py
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import core_entities as models


def create_comment(
    db: Session, *, task_id: UUID, user_id: str, body: str
) -> models.Comment:
    try:
        comment = models.Comment(
            task_id=str(task_id),
            user_id=user_id,
            body=body,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment
    except Exception:
        db.rollback()
        raise


def get_comment(db: Session, *, comment_id: UUID) -> Optional[models.Comment]:
    # SQLAlchemy 2.0 style
    return db.get(models.Comment, str(comment_id))


def get_comments_for_task(
    db: Session,
    *,
    task_id: UUID,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[models.Comment]:
    q = (
        db.query(models.Comment)
        .filter(models.Comment.task_id == str(task_id))
        .order_by(models.Comment.created_at.asc())
    )
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


def update_comment(
    db: Session, *, comment_id: UUID, body: str
) -> Optional[models.Comment]:
    comment = db.get(models.Comment, str(comment_id))
    if not comment:
        return None  # caller handles 404
    try:
        comment.body = body
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment
    except Exception:
        db.rollback()
        raise


def delete_comment(db: Session, *, comment_id: UUID) -> bool:
    comment = db.get(models.Comment, str(comment_id))
    if not comment:
        return False
    try:
        db.delete(comment)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
