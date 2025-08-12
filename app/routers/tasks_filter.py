# File: /app/routers/tasks_filter.py | Version: 2.6 | Title: Tasks Filter Router (sort+order + correct tags ANY/ALL)
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, and_, cast, exists, func, not_, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import Role, require_role
from app.db.session import get_db
from app.models.core_entities import List as ListModel
from app.models.core_entities import Space, Task, TaskAssignee, TaskTag, User, Workspace
from app.schemas.filters import (
    FilterOperator,
    FilterPayload,
    GroupBy,
    TagsMatch,
    TaskField,
)
from app.security import get_current_user

# Custom Field value may live in different module names depending on layout
try:
    from app.models.custom_fields import CustomFieldValue
except ImportError:  # pragma: no cover
    from app.models.core_entities import CustomFieldValue  # type: ignore

router = APIRouter(prefix="/workspaces", tags=["tasks-filter"])

# feature flag (spelled correctly 🙂)
HAS_ASSIGNEES = True

# sortable columns
_SORT_MAP = {
    "created_at": Task.created_at,
    "due_date": Task.due_date,
    "priority": Task.priority,
    "name": Task.name,
    "status": Task.status,
}


# ----------------------
# Scope & rule helpers
# ----------------------
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
        q = q.where(Space.workspace_id == s.workspace_id)

    return q


def _json_value_expr():
    # JSON shape assumed {"value": <actual>}
    return func.json_extract(CustomFieldValue.value, "$.value")


def _get_single_rule_expr(rule):
    field = rule.field
    op = rule.op
    val = rule.value

    # ----- Custom Field: key like cf_<definition_id>
    if isinstance(field, str) and field.startswith("cf_"):
        field_def_id = field.replace("cf_", "")

        base = and_(
            CustomFieldValue.task_id == Task.id,
            CustomFieldValue.field_definition_id == field_def_id,
        )
        v = _json_value_expr()

        if op == FilterOperator.eq:
            return exists(select(1).where(and_(base, cast(v, String) == str(val))))
        if op == FilterOperator.ne:
            return exists(select(1).where(and_(base, cast(v, String) != str(val))))
        if op == FilterOperator.contains:
            return exists(
                select(1).where(
                    and_(base, func.lower(cast(v, String)).contains(str(val).lower()))
                )
            )
        if op == FilterOperator.in_:
            return exists(
                select(1).where(
                    and_(base, cast(v, String).in_([str(x) for x in (val or [])]))
                )
            )
        if op == FilterOperator.not_in:
            return exists(
                select(1).where(
                    and_(base, not_(cast(v, String).in_([str(x) for x in (val or [])])))
                )
            )
        if op == FilterOperator.is_empty:
            no_row = not_(exists(select(1).where(base)))
            empty_value = exists(
                select(1).where(and_(base, or_(v.is_(None), cast(v, String) == "")))
            )
            return or_(no_row, empty_value)
        if op == FilterOperator.is_not_empty:
            return exists(
                select(1).where(and_(base, v.is_not(None), cast(v, String) != ""))
            )
        return None

    # ----- Native Task fields
    col_map = {
        TaskField.name: Task.name,
        TaskField.status: Task.status,
        TaskField.priority: Task.priority,
        TaskField.due_date: Task.due_date,
    }

    # Assignee rules
    if field == TaskField.assignee_id and HAS_ASSIGNEES:
        ex = select(TaskAssignee.id).where(TaskAssignee.task_id == Task.id)
        if op == FilterOperator.is_empty:
            return not_(exists(ex))
        if op == FilterOperator.is_not_empty:
            return exists(ex)
        if op == FilterOperator.eq:
            return exists(ex.where(TaskAssignee.user_id == val))
        if op == FilterOperator.in_:
            return exists(ex.where(TaskAssignee.user_id.in_(val or [])))
        if op == FilterOperator.not_in:
            return not_(exists(ex.where(TaskAssignee.user_id.in_(val or []))))
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
    exprs = []
    for r in payload.filters:
        e = _get_single_rule_expr(r)
        if e is not None:
            exprs.append(e)
    if exprs:
        q = q.where(and_(*exprs))
    return q


def _apply_sort(q, sort: Optional[str], order: str):
    if not sort:
        return q.order_by(Task.created_at.desc())
    col = _SORT_MAP.get(str(sort))
    if not col:
        return q.order_by(Task.created_at.desc())
    return q.order_by(col.desc() if str(order).lower() == "desc" else col.asc())


# -----------------------------
# NEW: tags ANY/ALL block
# -----------------------------
def _apply_tags_block(q, payload: FilterPayload):
    """
    Supports payload:
      {"tags": {"tag_ids": [<uuid>, ...], "match": "any"|"all"}}
    """
    tags_block = getattr(payload, "tags", None)
    if not tags_block:
        return q

    # payload.tags may be a dict or a Pydantic object
    if isinstance(tags_block, dict):
        tag_ids = tags_block.get("tag_ids") or tags_block.get("ids") or []
        match = (tags_block.get("match") or "any").lower()
    else:
        tag_ids = (
            getattr(tags_block, "tag_ids", None) or getattr(tags_block, "ids", []) or []
        )
        m = getattr(tags_block, "match", "any")
        match = m.value if isinstance(m, TagsMatch) else str(m).lower()

    tag_ids = [str(t) for t in (tag_ids or [])]
    if not tag_ids:
        return q

    if match == "all":
        # tasks that have *all* tag_ids
        sub = (
            select(TaskTag.task_id)
            .where(TaskTag.tag_id.in_(tag_ids))
            .group_by(TaskTag.task_id)
            .having(func.count(func.distinct(TaskTag.tag_id)) == len(tag_ids))
        )
        return q.where(Task.id.in_(sub))
    else:
        # ANY (default)
        sub = select(TaskTag.task_id).where(TaskTag.tag_id.in_(tag_ids))
        return q.where(Task.id.in_(sub))


# -----------------------------
# Query + response shaping
# -----------------------------
def _build_filtered_query(
    db: Session, payload: FilterPayload, sort: Optional[str], order: str
):
    q = select(Task).distinct()
    q = _apply_scope(q, payload)
    q = _apply_rules(q, payload)
    q = _apply_tags_block(q, payload)  # <- NEW
    q = _apply_sort(q, sort, order)
    q = q.offset(payload.offset).limit(payload.limit)
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


def _fetch_tasks(
    db: Session, payload: FilterPayload, sort: Optional[str], order: str
) -> List[Task]:
    rows = db.execute(_build_filtered_query(db, payload, sort, order))
    return list(rows.scalars().all())


def _group_tasks(db: Session, rows: List[Task], group_by: Optional[str]) -> List[dict]:
    if not group_by:
        return [{"group": None, "tasks": [_row_to_minimal_dict(t) for t in rows]}]

    # Group by Custom Field
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

    # Group by native fields
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


# -----------------------------
# Endpoint
# -----------------------------
@router.post("/{workspace_id}/tasks/filter")
def filter_tasks(
    workspace_id: UUID,
    payload: FilterPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    sort: Optional[str] = Query(
        None, pattern="^(created_at|due_date|priority|name|status)$"
    ),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    # guard: requester must be a member of this workspace
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(workspace_id),
        minimum=Role.MEMBER,
        message="Not allowed in this workspace.",
    )

    # enforce workspace scope alignment
    if payload.scope.workspace_id and str(payload.scope.workspace_id) != str(
        workspace_id
    ):
        raise HTTPException(status_code=400, detail="Workspace scope mismatch.")

    # if no narrower scope provided, apply workspace scope
    if not any(
        [payload.scope.list_id, payload.scope.folder_id, payload.scope.space_id]
    ):
        payload.scope.workspace_id = str(workspace_id)

    rows = _fetch_tasks(db, payload, sort, order)
    gb = (
        payload.group_by.value
        if isinstance(payload.group_by, GroupBy)
        else payload.group_by
    )
    grouped = _group_tasks(db, rows, gb)

    return {
        "count": sum(len(g["tasks"]) for g in grouped),
        "groups": grouped,
    }
