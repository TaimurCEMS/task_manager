# File: /tests/conftest.py | Version: 2.0
import pathlib
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- Ensure repo root is importable as a package root ---
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Canonical imports from the app ---
from app.db.base_class import Base
from app.main import app

# NOTE: We create a dedicated test engine/session and override get_db so the app uses it.
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite in tests
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Create schema once per test session ---
@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# --- Per-test DB session with rollback isolation ---
@pytest.fixture()
def db_session():
    connection = engine.connect()
    trans = connection.begin()
    try:
        session = TestingSessionLocal(bind=connection)
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()

# --- FastAPI TestClient that uses our test DB via dependency override ---
@pytest.fixture()
def client(db_session):
    from app.db.session import get_db  # import here to avoid circulars

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
