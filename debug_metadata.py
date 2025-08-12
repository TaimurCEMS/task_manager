# File: debug_metadata.py
from app.db.base_class import Base

print("✅ Metadata table keys:")
for table in Base.metadata.tables.keys():
    print("-", table)
