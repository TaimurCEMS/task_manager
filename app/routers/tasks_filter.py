# File: /app/routers/tasks_filter.py | Version: 1.1 (Corrected)
from __future__ import annotations

from typing import List
from uuid import UUID # Import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.filters import FilterPayload
from app.crud.filtering import fetch_tasks, group_tasks
# FIX 1: Corrected import path for get_db
from app.db.session import get_db
from app.security import get_current_user
from app.models.core_entities import User
# FIX 2: Use the correct, existing permission helper
from app.core.permissions import require_role, Role

router = APIRouter(prefix="/workspaces", tags=["tasks-filter"])


@router.post("/{workspace_id}/tasks/filter")
def filter_tasks(
    # FIX 3: Use UUID for type consistency
    workspace_id: UUID,
    payload: FilterPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified filtering endpoint per spec:

    - Permissions-first: validates the user is a member of the workspace in scope.
    - Supports filtering by standard fields and tags (any/all).
    - Optional grouping (status, priority, due_date, assignee_id).
    - Pagination via limit/offset in payload.
    """
    # 1) Permissions-first (spec requirement)
    # FIX 2: Use the correct permission check (require at least Guest/Member role)
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(workspace_id),
        minimum=Role.MEMBER, # Or Role.GUEST if guests can view/filter
        message="Not allowed in this workspace."
    )

    # 2) Server-side guard: payload scope must be consistent with path workspace
    # FIX 4: Correctly handle different scope types in the payload
    if payload.scope.workspace_id and str(payload.scope.workspace_id) != str(workspace_id):
        raise HTTPException(status_code=400, detail="Payload.workspace_id must match path workspace_id")
    
    # Ensure the payload's scope is set to the path's workspace_id if not provided at a lower level
    if not payload.scope.list_id and not payload.scope.folder_id and not payload.scope.space_id:
        payload.scope.workspace_id = str(workspace_id)


    # 3) Execute filtered query
    rows = fetch_tasks(db, payload)

    # 4) Grouping (optional)
    grouped = group_tasks(rows, payload.group_by.value if payload.group_by else None)

    return {
        "count": sum(len(g["tasks"]) for g in grouped),
        "groups": grouped,
    }

