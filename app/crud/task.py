# File: /app/crud/task.py | Version: 1.5 | Path: /app/crud/task.py
from __future__ import annotations

from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models import core_entities as models
from app.schemas import task as schema

# ---------------------------
# Core Task CRUD
# ---------------------------


def create_task(db: Session, data: schema.TaskCreate) -> models.Task:
    """
    Create a task. Accepts optional parent_task_id (subtask).
    Note: Model doesn't store space_id; it's validated in router.
    """
    try:
        task = models.Task(
            id=str(uuid4()),
            list_id=str(data.list_id),
            parent_task_id=str(data.parent_task_id) if data.parent_task_id else None,
            name=data.name,
            description=data.description,
            status=data.status or "to_do",
            priority=data.priority,
            due_date=data.due_date,
            # start_date / time_estimate not persisted in current model
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        # Assignees handling can be added later when model supports it
        return task
    except Exception:
        db.rollback()
        raise


def get_task(db: Session, task_id: UUID) -> Optional[models.Task]:
    return db.query(models.Task).filter_by(id=str(task_id)).first()


def get_tasks_by_list(db: Session, list_id: UUID) -> List[models.Task]:
    return db.query(models.Task).filter_by(list_id=str(list_id)).all()


def update_task(
    db: Session, task_id: UUID, data: schema.TaskUpdate
) -> Optional[models.Task]:
    task = get_task(db, task_id)
    if not task:
        return None

    patch = data.model_dump(exclude_unset=True)
    # Only set attrs that exist on the model
    for field, value in patch.items():
        if hasattr(task, field):
            setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: UUID) -> bool:
    task = get_task(db, task_id)
    if not task:
        return False
    db.delete(task)  # hard delete (no is_deleted field on Task model)
    db.commit()
    return True


# ---------------------------
# Subtasks helpers (Sprint 2)
# ---------------------------


def get_subtasks(db: Session, parent_task_id: UUID) -> List[models.Task]:
    return db.query(models.Task).filter_by(parent_task_id=str(parent_task_id)).all()


def create_subtask(
    db: Session, parent_task_id: UUID, data: schema.TaskCreate
) -> models.Task:
    """
    Convenience wrapper to create a subtask under a given parent.
    Uses the provided TaskCreate (must include list_id and name).
    """
    # Ensure parent exists
    parent = get_task(db, parent_task_id)
    if not parent:
        raise ValueError("Parent task not found")

    # Subtask must be in the same list as parent unless you design for cross-list
    if str(data.list_id) != parent.list_id:
        raise ValueError("Subtask must use the same list as its parent")

    # Create with parent_task_id set (Pydantic v2: model_copy)
    payload = data.model_copy(update={"parent_task_id": parent_task_id})
    return create_task(db, payload)


def _would_create_cycle(
    db: Session, child_id: str, new_parent_id: Optional[str]
) -> bool:
    """
    Returns True if moving 'child_id' under 'new_parent_id' would create a cycle.
    Walks up the parent chain of new_parent_id.
    """
    if new_parent_id is None:
        return False
    if new_parent_id == child_id:
        return True

    cursor = db.query(models.Task).filter_by(id=new_parent_id).first()
    while cursor is not None and cursor.parent_task_id is not None:
        if cursor.parent_task_id == child_id:
            return True
        cursor = db.query(models.Task).filter_by(id=cursor.parent_task_id).first()
    return False


def move_subtask(
    db: Session, child_task_id: UUID, new_parent_task_id: Optional[UUID]
) -> Optional[models.Task]:
    """
    Re-hang a task under a new parent (or detach by passing None).
    Prevents cycles. Requires same list (simple rule for now).
    """
    child = get_task(db, child_task_id)
    if not child:
        return None

    new_parent_id_str: Optional[str] = (
        str(new_parent_task_id) if new_parent_task_id else None
    )

    # If detaching
    if new_parent_id_str is None:
        child.parent_task_id = None
        db.commit()
        db.refresh(child)
        return child

    # Ensure new parent exists
    new_parent = get_task(db, new_parent_task_id)  # type: ignore[arg-type]
    if not new_parent:
        raise ValueError("New parent task not found")

    # Same-list rule (keeps MVP simple)
    if new_parent.list_id != child.list_id:
        raise ValueError("Child and new parent must be in the same list")

    # Cycle check
    if _would_create_cycle(db, child.id, new_parent_id_str):
        raise ValueError("Moving would create a cycle")

    child.parent_task_id = new_parent_id_str
    db.commit()
    db.refresh(child)
    return child


# ---------------------------
# Dependencies (placeholder)
# ---------------------------


def create_dependency(
    db: Session, data: schema.TaskDependencyCreate
) -> schema.TaskDependencyOut:
    # Return a synthesized dependency object (no DB storage yet)
    return schema.TaskDependencyOut(
        id=uuid4(),
        task_id=data.task_id,
        depends_on_id=data.depends_on_id,
    )


def get_dependencies_for_task(
    db: Session, task_id: UUID
) -> List[schema.TaskDependencyOut]:
    # No persistence yet; return empty list
    return []
