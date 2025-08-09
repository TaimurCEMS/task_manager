# File: /app/crud/comments.py | Version: 1.0 | Path: /app/crud/comments.py
from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import core_entities as models


def create_comment(db: Session, *, task_id: UUID, user_id: str, body: str) -> models.Comment:
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


def get_comments_for_task(db: Session, *, task_id: UUID) -> List[models.Comment]:
    return (
        db.query(models.Comment)
        .filter(models.Comment.task_id == str(task_id))
        .order_by(models.Comment.created_at.asc())
        .all()
    )
