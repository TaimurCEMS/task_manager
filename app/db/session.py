# File: /app/db/session.py | Version: 1.1 | Title: SQLAlchemy Session using Central Settings
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
