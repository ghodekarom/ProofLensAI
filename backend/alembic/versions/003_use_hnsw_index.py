"""Replace IVFFlat vector index with HNSW index for reliable semantic search

Revision ID: 003_use_hnsw_index
Revises: 002_add_chunks
Create Date: 2026-10-14 17:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "003_use_hnsw_index"
down_revision: str | None = "002_add_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the empty/unpartitioned IVFFlat index which returns 0 results on small corpora
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")

    # Create HNSW index with cosine distance operator — supports incremental row insertion
    # and provides fast, accurate approximate nearest-neighbour search without requiring
    # pre-calculated cluster centroids.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat
        ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )
