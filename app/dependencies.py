# File: /app/dependencies.py | Version: 1.1 | Path: /app/dependencies.py
from app.db.session import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
