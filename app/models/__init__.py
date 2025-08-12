# File: /app/models/__init__.py | Version: 1.2 | Title: Models Package Exports (unified CF exports)
from .core_entities import (
    Comment,
    Folder,
    List,
    Space,
    Tag,
    Task,
    TaskAssignee,
    TaskTag,
    TaskWatcher,
    TimeEntry,
    User,
    Workspace,
    WorkspaceMember,
)

# Prefer dedicated module if present, else fall back to core_entities
try:
    from .custom_fields import CustomFieldDefinition, CustomFieldValue, ListCustomField
except ImportError:
    from .core_entities import CustomFieldDefinition, CustomFieldValue, ListCustomField

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
