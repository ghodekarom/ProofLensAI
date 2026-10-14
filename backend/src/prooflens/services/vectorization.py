"""Vectorization service — chunks pages and persists embeddings to DB."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String
from sqlalchemy import Text as SAText
from sqlalchemy.orm import Session

from prooflens.core.logging import get_logger
from prooflens.db.models.chunk import EMBEDDING_COLUMN_TYPE, DocumentChunk
from prooflens.db.models.document import Document
from prooflens.domain.enums import DocumentStatus
from prooflens.services.chunking import ChunkingService, get_chunking_service
from prooflens.services.embeddings import EmbeddingProvider, get_embedding_provider

logger = get_logger("prooflens.services.vectorization")


class VectorizationService:
    """
    Orchestrates the chunk → embed → persist pipeline for a single document.

    Steps:
    1. Load extracted page text from the DB.
    2. Produce overlapping chunks via ChunkingService.
    3. Batch-embed all chunks via EmbeddingProvider.
    4. Persist DocumentChunk rows with embedding vectors.
    5. Update Document.chunk_count and advance status to READY.
    """

    def __init__(
        self,
        db: Session,
        chunker: ChunkingService | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self._db = db
        self._chunker = chunker or get_chunking_service()
        self._embedder = embedder or get_embedding_provider()

    def vectorize_document(self, document_id: uuid.UUID) -> int:
        """
        Chunk and embed all pages of a document; persist results.

        Args:
            document_id: UUID of the document to vectorize.

        Returns:
            Number of chunks created.

        Raises:
            ValueError: If the document is not found or has no pages.
        """
        document: Document | None = self._db.get(Document, document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found.")

        if not document.pages:
            logger.warning(f"Document {document_id} has no extracted pages; skipping vectorization.")
            return 0

        logger.info(f"Vectorizing document {document_id} ({len(document.pages)} pages).")

        # Step 1: Extract (page_number, text) tuples
        pages: list[tuple[int, str]] = [
            (page.page_number, page.text_content) for page in document.pages
        ]

        # Step 2: Chunk
        chunks = self._chunker.chunk_pages(document_id=str(document_id), pages=pages)
        if not chunks:
            logger.warning(f"No chunks produced for document {document_id}.")
            return 0

        # Step 3: Embed (batch)
        texts = [c.text_content for c in chunks]
        vectors = self._embedder.embed_texts(texts)

        # Step 4: Persist
        # On PostgreSQL the embedding column is vector(768); on SQLite (tests)
        # it is a Text column, so we JSON-encode the float list.
        _sqlite_fallback = isinstance(EMBEDDING_COLUMN_TYPE, (SAText, String))

        db_chunks: list[DocumentChunk] = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            embedding_value: Any = json.dumps(vector) if _sqlite_fallback else vector
            db_chunk = DocumentChunk(
                id=uuid.uuid4(),
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                text_content=chunk.text_content,
                embedding=embedding_value,
                page_numbers=chunk.page_numbers,
                token_count=chunk.token_count,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                chunk_metadata=chunk.metadata,
                created_at=datetime.now(UTC),
            )
            db_chunks.append(db_chunk)

        self._db.add_all(db_chunks)

        # Step 5: Update document metadata
        document.chunk_count = len(db_chunks)
        document.status = DocumentStatus.READY.value
        document.processed_at = datetime.now(UTC)
        self._db.commit()

        logger.info(f"Document {document_id}: vectorization complete ({len(db_chunks)} chunks).")
        return len(db_chunks)
