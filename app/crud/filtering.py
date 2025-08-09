# File: /app/crud/filtering.py | Version: 1.0
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, not_, func, select, literal
from app.schemas.filters import (
    FilterPayload,
    FilterOperator,
    TaskField,
    TagsMatch,
)
from app.models.task import Task
from app.models.list import List as ListModel
from app.models.space import Space
from app.models.workspace import Workspace
from app.models.tag import Tag
from app.models.task_tag import TaskTag
# Optional: if you have assignees in a link table
try:
    from app.models.task_assignee import TaskAssignee
    HAS_ASSIGNEES = True
except Exception:
    HAS_ASSIGNEES = False


def _apply_scope(q, payload: FilterPayload):
    s = payload.scope
    # Joins for hierarchy
    q = q.join(ListModel, ListModel.id == Task.list_id)\
         .join(Space, Space.id == ListModel.space_id)\
         .join(Workspace, Workspace.id == Space.workspace_id)

    if s.list_id:
        q = q.where(Task.list_id == s.list_id)
    elif s.folder_id:
        # Assuming List has folder_id (nullable)
        q = q.where(ListModel.folder_id == s.folder_id)
    elif s.space_id:
        q = q.where(ListModel.space_id == s.space_id)
    else:
        # workspace_id
        q = q.where(Space.workspace_id == s.workspace_id)

    return q


def _apply_single_rule(exprs: List, rule, aliases: Dict[str, Any]):
    field = rule.field
    op = rule.op
    val = rule.value

    # Map fields to ORM columns
    col_map = {
        TaskField.name: Task.name,
        TaskField.status: Task.status,
        TaskField.priority: Task.priority,
        TaskField.due_date: Task.due_date,
        TaskField.start_date: Task.start_date,
    }

    if field == TaskField.assignee_id and HAS_ASSIGNEES:
        # LEFT EXISTS style filter
        if op in (FilterOperator.is_empty, FilterOperator.is_not_empty):
            exists_q = select(TaskAssignee.id).where(TaskAssignee.task_id == Task.id)
            if op == FilterOperator.is_empty:
                exprs.append(not_(exists_q.exists()))
            else:
                exprs.append(exists_q.exists())
            return
        else:
            # value may be str or list
            exists_q = select(TaskAssignee.id).where(TaskAssignee.task_id == Task.id)
            if op in (FilterOperator.eq,):
                exists_q = exists_q.where(TaskAssignee.user_id == val)
            elif op in (FilterOperator.in_,):
                exists_q = exists_q.where(TaskAssignee.user_id.in_(val or []))
            elif op in (FilterOperator.ne,):
                exists_q = exists_q.where(TaskAssignee.user_id != val)
            elif op in (FilterOperator.not_in,):
                exists_q = exists_q.where(not_(TaskAssignee.user_id.in_(val or [])))
            exprs.append(exists_q.exists())
            return

    if field == TaskField.tag_ids:
        # handled by dedicated tags filter; ignore here
        return

    col = col_map.get(field)
    if col is None:
        return

    if op == FilterOperator.eq:
        exprs.append(col == val)
    elif op == FilterOperator.ne:
        exprs.append(col != val)
    elif op == FilterOperator.lt:
        exprs.append(col < val)
    elif op == FilterOperator.lte:
        exprs.append(col <= val)
    elif op == FilterOperator.gt:
        exprs.append(col > val)
    elif op == FilterOperator.gte:
        exprs.append(col >= val)
    elif op == FilterOperator.contains:
        exprs.append(func.lower(col).contains(str(val).lower()))
    elif op == FilterOperator.in_:
        exprs.append(col.in_(val or []))
    elif op == FilterOperator.not_in:
        exprs.append(not_(col.in_(val or [])))
    elif op == FilterOperator.is_empty:
        exprs.append(or_(col.is_(None), col == ""))
    elif op == FilterOperator.is_not_empty:
        exprs.append(and_(col.is_not(None), col != ""))


def _apply_rules(q, payload: FilterPayload) -> Tuple[Any, Optional[Any]]:
    """
    Returns (query, tags_having_clause)
    """
    exprs: List[Any] = []
    for r in payload.filters:
        _apply_single_rule(exprs, r, aliases={})

    if exprs:
        q = q.where(and_(*exprs))

    tags_having = None
    if payload.tags and payload.tags.tag_ids:
        # Build tag filtering using aggregation
        q = q.outerjoin(TaskTag, TaskTag.task_id == Task.id)
        q = q.group_by(Task.id)

        if payload.tags.match == TagsMatch.any:
            # at least one match
            tags_having = func.count(func.nullif(~TaskTag.tag_id.in_(payload.tags.tag_ids), True)) > 0
            # Equivalent: COUNT of matching tag rows > 0
            tags_having = func.count(
                func.nullif(~TaskTag.tag_id.in_(payload.tags.tag_ids), True)
            ) > 0
        else:
            # ALL: number of distinct matched tags for this task must equal len(tag_ids)
            tags_having = func.count(func.distinct(
                func.nullif(TaskTag.tag_id.notin_(payload.tags.tag_ids), None)
            )) == len(payload.tags.tag_ids)

        q = q.having(tags_having)

    return q, tags_having


def build_filtered_query(db: Session, payload: FilterPayload):
    q = select(Task)
    q = _apply_scope(q, payload)
    q, _ = _apply_rules(q, payload)
    q = q.offset(payload.offset).limit(payload.limit)
    return q


def fetch_tasks(db: Session, payload: FilterPayload) -> List[Task]:
    q = build_filtered_query(db, payload)
    return list(db.execute(q).scalars().all())


def group_tasks(rows: List[Task], group_by: Optional[str]) -> List[dict]:
    if not group_by:
        return [ {"group": None, "tasks": [_to_minimal_dict(t) for t in rows]} ]

    buckets: Dict[str, List[dict]] = {}
    for t in rows:
        if group_by == "status":
            key = t.status or "No Value"
            buckets.setdefault(key, []).append(_to_minimal_dict(t))
        elif group_by == "priority":
            key = t.priority or "No Value"
            buckets.setdefault(key, []).append(_to_minimal_dict(t))
        elif group_by == "due_date":
            key = (t.due_date.isoformat() if getattr(t, "due_date", None) else "No Value")
            buckets.setdefault(key, []).append(_to_minimal_dict(t))
        elif group_by == "assignee_id":
            # If you have many assignees per task, you might duplicate the task across assignees;
            # for MVP we'll use a single nullable field `assignee_id` if present on Task.
            key = getattr(t, "assignee_id", None) or "No Value"
            buckets.setdefault(str(key), []).append(_to_minimal_dict(t))
        else:
            # tag grouping (MVP note: requires eager load of tags if you want split-per-tag)
            key = "Tags"
            buckets.setdefault(key, []).append(_to_minimal_dict(t))

    return [{"group": k, "tasks": v} for k, v in buckets.items()]


def _to_minimal_dict(t: Task) -> Dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "status": getattr(t, "status", None),
        "priority": getattr(t, "priority", None),
        "due_date": getattr(t, "due_date", None),
        "start_date": getattr(t, "start_date", None),
        "list_id": getattr(t, "list_id", None),
    }
