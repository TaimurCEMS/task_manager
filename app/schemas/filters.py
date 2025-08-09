# File: /app/schemas/filters.py | Version: 1.0
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union, Any
from pydantic import BaseModel, Field, validator


class FilterOperator(str, Enum):
    eq = "eq"
    ne = "ne"
    lt = "lt"
    lte = "lte"
    gt = "gt"
    gte = "gte"
    contains = "contains"
    in_ = "in"          # list of values
    not_in = "not_in"   # list of values
    is_empty = "is_empty"
    is_not_empty = "is_not_empty"


# Canonical task fields available for filtering in MVP (per spec)
class TaskField(str, Enum):
    name = "name"
    status = "status"
    priority = "priority"
    due_date = "due_date"
    start_date = "start_date"
    assignee_id = "assignee_id"  # optional (if you have TaskAssignees link table)
    tag_ids = "tag_ids"          # special-cased; use TagsFilter instead
    # Custom fields will be added in Phase 5C


class FilterRule(BaseModel):
    field: TaskField
    op: FilterOperator
    value: Optional[Union[str, int, float, List[Any]]] = None


class TagsMatch(str, Enum):
    any = "any"
    all = "all"


class TagsFilter(BaseModel):
    tag_ids: List[str] = Field(default_factory=list)  # string UUIDs in your app
    match: TagsMatch = TagsMatch.any


class Scope(BaseModel):
    """
    Query scope chooses the dataset before filters.
    Provide exactly one of: list_id, folder_id, space_id, or workspace_id.
    """
    list_id: Optional[str] = None
    folder_id: Optional[str] = None
    space_id: Optional[str] = None
    workspace_id: Optional[str] = None

    @validator("workspace_id", always=True)
    def at_least_one(cls, v, values):
        if not (v or values.get("space_id") or values.get("folder_id") or values.get("list_id")):
            raise ValueError(
                "Provide one scope: workspace_id or space_id or folder_id or list_id"
            )
        return v


class GroupBy(str, Enum):
    status = "status"
    assignee_id = "assignee_id"
    priority = "priority"
    due_date = "due_date"
    tag_ids = "tag_ids"  # when grouping by tags, tasks may appear in multiple groups


class FilterPayload(BaseModel):
    scope: Scope
    filters: List[FilterRule] = Field(default_factory=list)
    tags: Optional[TagsFilter] = None
    group_by: Optional[GroupBy] = None
    limit: int = Field(default=200, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
