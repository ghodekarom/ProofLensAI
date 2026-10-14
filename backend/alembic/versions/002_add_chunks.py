"""Add document_chunks table with pgvector embedding column

Revision ID: 002_add_chunks
Revises: 001_initial_schema
Create Date: 2026-10-13 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_add_chunks"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Ensure pgvector extension exists (safe if already added in 001)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Table: document_chunks
    # Uses the `vector` type from pgvector for the embedding column.
    # Index type: ivfflat with cosine distance — optimal for semantic search
    # on moderate corpus sizes (up to ~1M chunks). Requires at least one row
    # before ANALYZE can set the number of lists; lists=100 is a safe default.
    op.execute(
        """
        CREATE TABLE document_chunks (
            id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id     UUID            NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index     INTEGER         NOT NULL,
            text_content    TEXT            NOT NULL,
            embedding       vector(768),
            page_numbers    JSONB           NOT NULL DEFAULT '[]',
            token_count     INTEGER         NOT NULL DEFAULT 0,
            start_char      INTEGER         NOT NULL DEFAULT 0,
            end_char        INTEGER         NOT NULL DEFAULT 0,
            chunk_metadata  JSONB           NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            CONSTRAINT uq_document_chunks_document_idx UNIQUE (document_id, chunk_index)
        )
        """
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # IVFFlat index for approximate nearest-neighbour search using cosine distance.
    # The index is created but the number of lists should be tuned post-ingest.
    op.execute(
        """
        CREATE INDEX ix_document_chunks_embedding_ivfflat
        ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.drop_index("ix_document_chunks_document_id", "document_chunks")
    op.drop_table("document_chunks")
