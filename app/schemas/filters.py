# File: /app/schemas/filters.py | Version: 1.2 | Title: Filters & Grouping Schemas
from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class FilterOperator(str, Enum):
    eq = "eq"
    ne = "ne"
    lt = "lt"
    lte = "lte"
    gt = "gt"
    gte = "gte"
    contains = "contains"
    in_ = "in"
    not_in = "not_in"
    is_empty = "is_empty"
    is_not_empty = "is_not_empty"


class TaskField(str, Enum):
    name = "name"
    status = "status"
    priority = "priority"
    due_date = "due_date"
    start_date = "start_date"
    assignee_id = "assignee_id"
    tag_ids = "tag_ids"


class FilterRule(BaseModel):
    field: Union[TaskField, str]
    op: FilterOperator
    value: Optional[Union[str, int, float, List[Any]]] = None


class TagsMatch(str, Enum):
    any = "any"
    all = "all"


class TagsFilter(BaseModel):
    tag_ids: List[str] = Field(default_factory=list)
    match: TagsMatch = TagsMatch.any


class Scope(BaseModel):
    list_id: Optional[str] = None
    folder_id: Optional[str] = None
    space_id: Optional[str] = None
    workspace_id: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one_scope(self) -> "Scope":
        if not any([self.list_id, self.folder_id, self.space_id, self.workspace_id]):
            raise ValueError(
                "Provide one scope: workspace_id, space_id, folder_id, or list_id"
            )
        return self


class GroupBy(str, Enum):
    status = "status"
    assignee_id = "assignee_id"
    priority = "priority"
    due_date = "due_date"
    tag_ids = "tag_ids"


class FilterPayload(BaseModel):
    scope: Scope
    filters: List[FilterRule] = Field(default_factory=list)
    tags: Optional[TagsFilter] = None
    group_by: Optional[Union[GroupBy, str]] = None
    limit: int = Field(default=200, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
