# File: app/crud/task.py | Version: 1.1 | Path: /app/crud/task.py

from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app import models, schemas

def create_task(db: Session, data: schemas.task.TaskCreate):
    try:
        # Step 1: Create task base object
        task = models.task.Task(
            name=data.name,
            description=data.description,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            start_date=data.start_date,
            time_estimate=data.time_estimate,
            list_id=str(data.list_id),
            space_id=str(data.space_id),
            parent_task_id=str(data.parent_task_id) if data.parent_task_id else None
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Step 2: Assign users if any
        if data.assignee_ids:
            for user_id in data.assignee_ids:
                assignee = models.task.TaskAssignee(task_id=task.id, user_id=str(user_id))
                db.add(assignee)
            db.commit()

        return task

    except Exception as e:
        db.rollback()
        print("❌ Error in create_task():", str(e))
        raise
