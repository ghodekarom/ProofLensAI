"""Pytest global configuration and fixtures."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure test environment settings BEFORE any app imports
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "true"
os.environ["LOCAL_STORAGE_PATH"] = "./var/test_uploads"

from prooflens.db.base import Base
from prooflens.db.session import get_db_session
from prooflens.main import app
from prooflens.services.embeddings import StubEmbeddingProvider
from prooflens.services.llm import StubLLMService
from prooflens.storage.local_filesystem import LocalFilesystemStorage


@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped in-memory SQLite database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_engine) -> Generator[Session]:
    """Database session fixture per test."""
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = session_factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(test_engine, monkeypatch, tmp_path: Path) -> Generator[TestClient]:
    """FastAPI TestClient fixture with overridden DB dependency and temporary storage."""
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    test_storage = LocalFilesystemStorage(base_dir=tmp_path)
    stub_embedder = StubEmbeddingProvider(dims=768)
    stub_llm = StubLLMService()

    monkeypatch.setattr("prooflens.services.workspaces.get_storage_service", lambda: test_storage)
    monkeypatch.setattr("prooflens.services.documents.get_storage_service", lambda: test_storage)
    monkeypatch.setattr("prooflens.services.ingestion.get_storage_service", lambda: test_storage)
    monkeypatch.setattr("prooflens.services.ingestion.get_session_factory", lambda: session_factory)
    # Replace real Gemini embedding and LLM calls with stubs in all integration tests
    monkeypatch.setattr("prooflens.services.embeddings.get_embedding_provider", lambda: stub_embedder)
    monkeypatch.setattr("prooflens.services.vectorization.get_embedding_provider", lambda: stub_embedder)
    monkeypatch.setattr("prooflens.services.llm.get_llm_service", lambda: stub_llm)
    monkeypatch.setattr("prooflens.api.v1.routes.analysis.get_llm_service", lambda: stub_llm)
    monkeypatch.setattr("prooflens.services.comparison.get_llm_service", lambda: stub_llm)

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

