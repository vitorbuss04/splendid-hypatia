import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure APP_ENV is test before importing application
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///data/test.db"

from backend.database import Base, get_db
from backend import models
from app import app

# Test SQLite engine
TEST_DB_URL = "sqlite:///data/test.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Create all tables once for session
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    # Cleanup after session
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db():
    # Fresh connection / transaction per test function
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def make_user(client):
    def _make(email: str = "test@example.com", password: str = "secret123", full_name: str = "Test User"):
        resp = client.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "company_name": "Test 3D Studio"
        })
        assert resp.status_code == 201
        data = resp.json()
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        return {"user": data["user"], "token": token, "headers": headers}
    return _make
