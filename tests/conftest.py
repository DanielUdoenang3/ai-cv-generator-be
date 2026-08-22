import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.utils.database import Base, get_db
from app.models import Admin, Client, Submission, Conversation, Message, SubmissionActivity

# Create in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh in-memory database schema for each test function.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    FastAPI TestClient fixture configured with in-memory DB override.
    """
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def mock_cloudinary():
    """
    Mocks Cloudinary uploader to prevent external HTTP API calls during tests.
    """
    fake_response = {
        "secure_url": "https://res.cloudinary.com/demo/image/upload/v1600000000/ai_cv_generator/test.pdf",
        "public_id": "ai_cv_generator/test",
        "original_filename": "test.pdf",
        "resource_type": "raw",
        "format": "pdf",
        "bytes": 2048,
    }
    with patch("cloudinary.uploader.upload", return_value=fake_response) as mock_upload:
        yield mock_upload
