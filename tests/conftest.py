import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.database import Base, get_db
from src.services.storage_service import get_storage_service
from src.main import app


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service for testing."""
    mock = MagicMock()
    mock.is_available.return_value = True
    mock.upload_file.return_value = "documents/1/test.pdf"
    return mock


@pytest.fixture
def mock_storage_unavailable():
    """Create a mock storage service that is unavailable."""
    mock = MagicMock()
    mock.is_available.return_value = False
    return mock


@pytest.fixture
def client(db_session, mock_storage_service):
    """Create a test client with dependency overrides."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_storage_unavailable(db_session, mock_storage_unavailable):
    """Create a test client with unavailable storage."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: mock_storage_unavailable
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf():
    """Sample PDF file for testing."""
    return ("test.pdf", b"%PDF-1.4 sample content", "application/pdf")


@pytest.fixture
def sample_txt():
    """Sample text file for testing."""
    return ("test.txt", b"Hello world", "text/plain")


@pytest.fixture
def sample_docx():
    """Sample DOCX file for testing."""
    return (
        "test.docx",
        b"PK\x03\x04 docx content",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.fixture
def sample_markdown():
    """Sample markdown file for testing."""
    return ("test.md", b"# Hello World", "text/markdown")


@pytest.fixture
def sample_invalid_file():
    """Sample invalid file type for testing."""
    return ("test.png", b"\x89PNG\r\n\x1a\n", "image/png")


@pytest.fixture
def sample_large_file():
    """Sample file exceeding size limit."""
    return ("large.pdf", b"x" * (51 * 1024 * 1024), "application/pdf")
