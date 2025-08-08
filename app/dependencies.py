# File: app/dependencies.py | Version: 1.0 | Path: /app/dependencies.py

from app.db.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
