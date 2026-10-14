"""DocumentChunk ORM model — stores vectorized text segments with page provenance."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# pgvector is required in production (PostgreSQL) but may be absent in test
# environments running SQLite. Use a JSON Text column as a safe fallback so that
# SQLite-based unit tests can create tables without the pgvector extension.
try:
    from pgvector.sqlalchemy import Vector as _PgVector

    EMBEDDING_COLUMN_TYPE = _PgVector(768)
except ImportError:  # pragma: no cover
    EMBEDDING_COLUMN_TYPE = Text()  # type: ignore[assignment]

from prooflens.db.base import Base

if TYPE_CHECKING:
    from prooflens.db.models.document import Document

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


def utcnow() -> datetime:
    return datetime.now(UTC)


class DocumentChunk(Base):
    """
    Represents a bounded, overlapping text segment derived from a document.

    Each chunk stores:
    - The raw text content.
    - Its 768-dimension embedding vector (pgvector on PostgreSQL; Text on SQLite).
    - A list of page numbers from which the text was drawn (provenance).
    - Positional metadata (chunk_index, token_count, char offsets).
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_idx"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    # On PostgreSQL: vector(768) column via pgvector.
    # On SQLite (tests): Text column storing a JSON-serialised float list.
    embedding: Mapped[Any] = mapped_column(EMBEDDING_COLUMN_TYPE, nullable=True)
    # Ordered list of contributing 1-based page numbers, e.g. [3] or [3, 4]
    page_numbers: Mapped[list[Any]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_char: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    end_char: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
