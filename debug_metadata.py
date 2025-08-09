# File: debug_metadata.py
from app.db.base_class import Base

from app.models import (
    core_entities,
    list,
    task,
    user,
    workspace_member,
    tag,
    comment,
    time_entry,
    task_assignee,
)

print("✅ Metadata table keys:")
for table in Base.metadata.tables.keys():
    print("-", table)
