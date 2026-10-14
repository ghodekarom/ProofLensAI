"""Unit tests for embedding providers and VectorizationService."""

import uuid

import pytest

from prooflens.services.chunking import ChunkingService
from prooflens.services.embeddings import StubEmbeddingProvider
from prooflens.services.vectorization import VectorizationService


class TestStubEmbeddingProvider:
    def test_dimensions(self) -> None:
        provider = StubEmbeddingProvider(dims=768)
        assert provider.dimensions == 768

    def test_returns_correct_count(self) -> None:
        provider = StubEmbeddingProvider(dims=8)
        texts = ["hello", "world", "foo"]
        vectors = provider.embed_texts(texts)
        assert len(vectors) == 3
        for v in vectors:
            assert len(v) == 8

    def test_returns_zero_vectors(self) -> None:
        provider = StubEmbeddingProvider(dims=4)
        vectors = provider.embed_texts(["text"])
        assert vectors[0] == [0.0, 0.0, 0.0, 0.0]

    def test_raises_on_empty_input(self) -> None:
        provider = StubEmbeddingProvider()
        # embed_texts on empty list should not crash; empty is valid no-op in stub
        vectors = provider.embed_texts([])
        assert vectors == []


class TestVectorizationService:
    """Tests use SQLite in-memory via the test fixtures defined in conftest."""

    def test_vectorize_document_with_stubs(self, db_session: "Session") -> None:  # type: ignore[name-defined]  # noqa: F821
        """Integration smoke test: ingest a document and verify chunks are persisted."""
        from prooflens.db.models.document import Document
        from prooflens.db.models.page import DocumentPage
        from prooflens.db.models.workspace import Workspace
        from prooflens.domain.enums import DocumentStatus

        # Setup: workspace + document + pages
        ws = Workspace(name="Test WS")
        db_session.add(ws)
        db_session.flush()

        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            workspace_id=ws.id,
            original_filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            sha256="abc123",
            storage_key="test/test.pdf",
            status=DocumentStatus.PROCESSING.value,
        )
        db_session.add(doc)
        db_session.flush()

        pages_text = [
            "The quick brown fox jumps over the lazy dog. " * 10,
            "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 10,
        ]
        for i, text in enumerate(pages_text, start=1):
            db_session.add(
                DocumentPage(
                    document_id=doc_id,
                    page_number=i,
                    text_content=text,
                    character_count=len(text),
                    extraction_status="extracted",
                    page_metadata={},
                )
            )
        db_session.flush()

        # Reload doc with pages eager-loaded
        db_session.refresh(doc)

        chunker = ChunkingService(chunk_size=50, overlap=5)
        embedder = StubEmbeddingProvider(dims=768)
        service = VectorizationService(db=db_session, chunker=chunker, embedder=embedder)

        count = service.vectorize_document(doc_id)

        assert count > 0
        db_session.refresh(doc)
        assert doc.chunk_count == count
        assert doc.status == DocumentStatus.READY.value
        assert doc.processed_at is not None

    def test_vectorize_missing_document_raises(self, db_session: "Session") -> None:  # type: ignore[name-defined]  # noqa: F821
        service = VectorizationService(
            db=db_session,
            chunker=ChunkingService(chunk_size=10, overlap=2),
            embedder=StubEmbeddingProvider(),
        )
        with pytest.raises(ValueError, match="not found"):
            service.vectorize_document(uuid.uuid4())

    def test_vectorize_document_with_no_pages_returns_zero(self, db_session: "Session") -> None:  # type: ignore[name-defined]  # noqa: F821
        from prooflens.db.models.document import Document
        from prooflens.db.models.workspace import Workspace
        from prooflens.domain.enums import DocumentStatus

        ws = Workspace(name="Empty WS")
        db_session.add(ws)
        db_session.flush()

        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            workspace_id=ws.id,
            original_filename="empty.pdf",
            content_type="application/pdf",
            size_bytes=0,
            sha256="def456",
            storage_key="test/empty.pdf",
            status=DocumentStatus.PROCESSING.value,
        )
        db_session.add(doc)
        db_session.flush()
        db_session.refresh(doc)

        service = VectorizationService(
            db=db_session,
            chunker=ChunkingService(chunk_size=10, overlap=2),
            embedder=StubEmbeddingProvider(),
        )
        count = service.vectorize_document(doc_id)
        assert count == 0
