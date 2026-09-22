"""
Pytest configuration and fixtures for backend tests.

Uses a file-based SQLite test database.
Tables are created fresh before each test and dropped after.

Key design:
- `setup_test_db` (autouse): creates/drops tables around every test
- `db`: provides a raw SQLAlchemy session for unit tests
- `client`: provides a FastAPI TestClient with the DB dependency overridden
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.dependencies import get_db
from app.models import Base  # Import all models so metadata is populated

TEST_DB_PATH = "./test_expense_splitter.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    """
    Create all tables at the start of each test, drop at the end.
    autouse=True ensures this runs for every test automatically.
    """
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    # Clean up the test DB file if it exists
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


@pytest.fixture
def db():
    """Provide a raw SQLAlchemy session (for unit tests that need direct DB access)."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """
    FastAPI TestClient with the get_db dependency overridden to use the test database.
    Each request within a test shares the same test_engine but gets its own session.
    """
    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
