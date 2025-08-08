# File: app/db/base_class.py | Version: 1.0 | Path: /app/db/base_class.py
from sqlalchemy.orm import declarative_base

# Single, authoritative Base for all models
Base = declarative_base()
