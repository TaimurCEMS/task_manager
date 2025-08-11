# File: /app/models/__init__.py | Version: 1.2 | Title: Models Package Exports (unified CF exports)
from .core_entities import (
    User,
    Workspace,
    WorkspaceMember,
    Space,
    Folder,
    List,
    Task,
    Comment,
    TimeEntry,
    TaskAssignee,
    Tag,
    TaskTag,
    TaskWatcher,
)

# Prefer dedicated module if present, else fall back to core_entities
try:
    from .custom_fields import CustomFieldDefinition, ListCustomField, CustomFieldValue
except ImportError:
    from .core_entities import CustomFieldDefinition, ListCustomField, CustomFieldValue

__all__ = [
    "User",
    "Workspace",
    "WorkspaceMember",
    "Space",
    "Folder",
    "List",
    "Task",
    "Comment",
    "TimeEntry",
    "TaskAssignee",
    "Tag",
    "TaskTag",
    "TaskWatcher",
    "CustomFieldDefinition",
    "ListCustomField",
    "CustomFieldValue",
]
