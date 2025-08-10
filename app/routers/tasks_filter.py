from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, not_, func, select, exists, cast, String
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security import get_current_user
from app.core.permissions import require_role, Role
from app.schemas.filters import (
    FilterPayload,
    FilterOperator,
    TaskField,
    TagsMatch,
    GroupBy,
)
from app.models.core_entities import (
    Task,
    List as ListModel,
    Space,
    Workspace,
    TaskAssignee,
    Tag,
    TaskTag,
    User,
)
from app.models.custom_fields import CustomFieldValue

router = APIRouter(prefix="/workspaces", tags=["tasks-filter"])

# Feature flag in case assignees are optional in your instance
HAS_ASSIGNEES = True


# ---------------------------
# Query-building helpers
# ---------------------------

def _apply_scope(q, payload: FilterPayload):
    s = payload.scope

    q = (
        q.join(ListModel, ListModel.id == Task.list_id)
         .join(Space, Space.id == ListModel.space_id)
         .join(Workspace, Workspace.id == Space.workspace_id)
    )

    if s.list_id:
        q = q.where(Task.list_id == s.list_id)
    elif s.folder_id:
        q = q.where(ListModel.folder_id == s.folder_id)
    elif s.space_id:
        q = q.where(ListModel.space_id == s.space_id)
    else:
        # Default to workspace scope (guards cross-workspace peeking)
        q = q.where(Space.workspace_id == s.workspace_id)

    return q


def _json_value_expr():
    """
    Cross-dialect way to read CustomFieldValue.value['value'].
    On SQLite: json_extract(value, '$.value')
    """
    return func.json_extract(CustomFieldValue.value, "$.value")


def _get_single_rule_expr(rule):
    field = rule.field
    op = rule.op
    val = rule.value

    # ---------- Custom Field Rules: "cf_<field_definition_id>" ----------
    if isinstance(field, str) and field.startswith("cf_"):
        field_def_id = field.replace("cf_", "")

        base_exists = select(1).where(
            and_(
                CustomFieldValue.task_id == Task.id,
                CustomFieldValue.field_definition_id == field_def_id,
            )
        )

        v = _json_value_expr()

        if op == FilterOperator.eq:
            return exists(base_exists.where(cast(v, String) == str(val)))
        if op == FilterOperator.ne:
            return exists(base_exists.where(cast(v, String) != str(val)))
        if op == FilterOperator.contains:
            return exists(base_exists.where(func.lower(cast(v, String)).contains(str(val).lower())))
        if op == FilterOperator.in_:
            return exists(base_exists.where(cast(v, String).in_([str(x) for x in (val or [])])))
        if op == FilterOperator.not_in:
            return exists(base_exists.where(not_(cast(v, String).in_([str(x) for x in (val or [])]))))
        if op == FilterOperator.is_empty:
            no_row = not_(exists(base_exists))
            empty_value = exists(base_exists.where(or_(v.is_(None), cast(v, String) == "")))
            return or_(no_row, empty_value)
        if op == FilterOperator.is_not_empty:
            return exists(base_exists.where(and_(v.is_not(None), cast(v, String) != "")))

        return None

    # ---------- Standard Task Field Rules ----------
    col_map = {
        TaskField.name: Task.name,
        TaskField.status: Task.status,
        TaskField.priority: Task.priority,
        TaskField.due_date: Task.due_date,
    }

    if field == TaskField.assignee_id and HAS_ASSIGNEES:
        exists_q = select(TaskAssignee.id).where(TaskAssignee.task_id == Task.id)
        if op == FilterOperator.is_empty:
            return not_(exists(exists_q))
        if op == FilterOperator.is_not_empty:
            return exists(exists_q)
        if op == FilterOperator.eq:
            return exists(exists_q.where(TaskAssignee.user_id == val))
        if op == FilterOperator.in_:
            return exists(exists_q.where(TaskAssignee.user_id.in_(val or [])))
        if op == FilterOperator.not_in:
            return not_(exists(exists_q.where(TaskAssignee.user_id.in_(val or []))))
        return None

    col = col_map.get(field)
    if col is None:
        return None

    if op == FilterOperator.eq:
        return col == val
    if op == FilterOperator.ne:
        return col != val
    if op == FilterOperator.lt:
        return col < val
    if op == FilterOperator.lte:
        return col <= val
    if op == FilterOperator.gt:
        return col > val
    if op == FilterOperator.gte:
        return col >= val
    if op == FilterOperator.contains:
        return func.lower(col).contains(str(val).lower())
    if op == FilterOperator.in_:
        return col.in_(val or [])
    if op == FilterOperator.not_in:
        return not_(col.in_(val or []))
    if op == FilterOperator.is_empty:
        return or_(col.is_(None), col == "")
    if op == FilterOperator.is_not_empty:
        return and_(col.is_not(None), col != "")

    return None


def _apply_rules(q, payload: FilterPayload):
    expressions = []
    for r in payload.filters:
        expr = _get_single_rule_expr(r)
        if expr is not None:
            expressions.append(expr)

    if expressions:
        q = q.where(and_(*expressions))
    return q


def _build_filtered_query(db: Session, payload: FilterPayload):
    q = select(Task).distinct()
    q = _apply_scope(q, payload)
    q = _apply_rules(q, payload)

    if payload.tags and payload.tags.tag_ids:
        q = q.join(TaskTag, TaskTag.task_id == Task.id)
        q = q.where(TaskTag.tag_id.in_(payload.tags.tag_ids))
        if payload.tags.match == TagsMatch.all:
            q = q.group_by(Task.id).having(
                func.count(TaskTag.tag_id.distinct()) == len(payload.tags.tag_ids)
            )

    q = q.order_by(Task.created_at.desc()).offset(payload.offset).limit(payload.limit)
    return q


def _row_to_minimal_dict(t: Task) -> Dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "status": getattr(t, "status", None),
        "priority": getattr(t, "priority", None),
        "due_date": getattr(t, "due_date", None),
        "list_id": str(t.list_id),
    }


def _fetch_tasks(db: Session, payload: FilterPayload) -> List[Task]:
    rows = db.execute(_build_filtered_query(db, payload))
    return list(rows.scalars().all())


def _group_tasks(db: Session, rows: List[Task], group_by: Optional[str]) -> List[dict]:
    if not group_by:
        return [{"group": None, "tasks": [_row_to_minimal_dict(t) for t in rows]}]

    if isinstance(group_by, str) and group_by.startswith("cf_"):
        field_def_id = group_by.replace("cf_", "")
        buckets: Dict[str, List[dict]] = {}
        for t in rows:
            val_expr = (
                select(_json_value_expr())
                .where(
                    and_(
                        CustomFieldValue.task_id == t.id,
                        CustomFieldValue.field_definition_id == field_def_id,
                    )
                )
                .limit(1)
            )
            cf_value = db.execute(val_expr).scalar()
            key = str(cf_value) if cf_value not in (None, "") else "No Value"
            buckets.setdefault(key, []).append(_row_to_minimal_dict(t))
        return [{"group": k, "tasks": v} for k, v in buckets.items()]

    buckets: Dict[str, List[dict]] = {}
    for t in rows:
        if group_by == "status":
            key = t.status or "No Value"
        elif group_by == "priority":
            key = t.priority or "No Value"
        elif group_by == "due_date":
            key = t.due_date.isoformat() if getattr(t, "due_date", None) else "No Value"
        elif group_by == "assignee_id" and HAS_ASSIGNEES:
            key = "Assignee"
        else:
            key = "Other"
        buckets.setdefault(str(key), []).append(_row_to_minimal_dict(t))
    return [{"group": k, "tasks": v} for k, v in buckets.items()]


# ---------------------------
# Router endpoint
# ---------------------------

@router.post("/{workspace_id}/tasks/filter")
def filter_tasks(
    workspace_id: UUID,
    payload: FilterPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(workspace_id),
        minimum=Role.MEMBER,
        message="Not allowed in this workspace.",
    )

    if payload.scope.workspace_id and str(payload.scope.workspace_id) != str(workspace_id):
        raise HTTPException(status_code=400, detail="Workspace scope mismatch.")
    
    if not any([payload.scope.list_id, payload.scope.folder_id, payload.scope.space_id]):
        payload.scope.workspace_id = str(workspace_id)

    rows = _fetch_tasks(db, payload)
    gb = payload.group_by.value if isinstance(payload.group_by, GroupBy) else payload.group_by
    grouped = _group_tasks(db, rows, gb)

    return {
        "count": sum(len(g["tasks"]) for g in grouped),
        "groups": grouped,
    }
