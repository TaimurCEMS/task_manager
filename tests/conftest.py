# File: tests/conftest.py | Version: 1.1 | Path: /tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Pull Base/get_db from your app DB package
from app.db import Base, get_db
from app.main import app

# --- Test DB engine: one shared in-memory SQLite for the whole test run ---
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

@pytest.fixture(scope="session", autouse=True)
def create_schema():
    """
    Ensure all models are registered on Base.metadata,
    then create/drop the schema once per test session.
    """
    # Import the single source of truth so SQLAlchemy sees every table
    import app.models.core_entities  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def db_session():
    """
    Wrap each test in a transaction that rolls back, so tests are isolated.
    """
    connection = engine.connect()
    trans = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()

@pytest.fixture()
def client(db_session):
    """
    Override FastAPI's get_db dependency to use our test session.
    """
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
