"""Semantic retrieval service — finds relevant chunks via pgvector ANN search."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from prooflens.core.config import get_settings
from prooflens.core.logging import get_logger
from prooflens.services.embeddings import EmbeddingProvider, get_embedding_provider

logger = get_logger("prooflens.services.retrieval")


@dataclass
class RetrievedChunk:
    """A single retrieved passage with full provenance."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text_content: str
    page_numbers: list[int]
    cosine_distance: float

    @property
    def cosine_similarity(self) -> float:
        """Convert distance to similarity (0–1 scale)."""
        return 1.0 - self.cosine_distance


class RetrievalService:
    """
    Semantic retrieval over a workspace's document chunks.

    Uses pgvector's `<=>` cosine distance operator with an HNSW index
    for fast approximate nearest-neighbour search.

    The query is embedded using the same provider / model as ingestion to
    ensure the vector space is compatible.
    """

    def __init__(
        self,
        db: Session,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self._db = db
        self._embedder = embedder or get_embedding_provider()
        self._settings = get_settings()

    def search(
        self,
        workspace_id: uuid.UUID,
        query: str,
        top_k: int | None = None,
        distance_threshold: float | None = None,
        document_id: uuid.UUID | None = None,
    ) -> list[RetrievedChunk]:
        """
        Embed ``query`` and return the top-K most similar chunks from the workspace.

        Args:
            workspace_id: Scope the search to documents in this workspace.
            query: Free-text search query from the user.
            top_k: Number of results to return; defaults to ``RETRIEVAL_TOP_K_DEFAULT``.
            distance_threshold: Filter out chunks with cosine distance above this value.
                                 None = use the global setting (which may also be None = no filter).
            document_id: Optional UUID to restrict search to a specific document.

        Returns:
            List of RetrievedChunk, ordered by ascending cosine distance (most similar first).
        """
        settings = self._settings
        k = min(top_k or settings.RETRIEVAL_TOP_K_DEFAULT, settings.RETRIEVAL_TOP_K_MAX)
        threshold = distance_threshold if distance_threshold is not None else settings.RETRIEVAL_DISTANCE_THRESHOLD

        if not query.strip():
            raise ValueError("Search query must not be empty.")

        # Embed the query using the retrieval task type for better accuracy
        [query_vector] = self._embedder.embed_texts([query], task_type="RETRIEVAL_QUERY")
        vector_literal = f"[{','.join(str(v) for v in query_vector)}]"

        is_sqlite = bool(self._db.bind and self._db.bind.dialect.name == "sqlite")
        doc_filter = "AND d.id = :document_id" if document_id is not None else ""
        params: dict[str, Any] = {
            "workspace_id": workspace_id.hex if is_sqlite else str(workspace_id),
            "top_k": k,
        }
        if document_id is not None:
            params["document_id"] = document_id.hex if is_sqlite else str(document_id)

        if is_sqlite:
            sql = text(
                f"""
                SELECT
                    dc.id           AS chunk_id,
                    dc.document_id,
                    dc.chunk_index,
                    dc.text_content,
                    dc.page_numbers,
                    0.0             AS cosine_distance
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE
                    d.workspace_id = :workspace_id
                    AND d.status   = 'ready'
                    {doc_filter}
                LIMIT :top_k
                """
            )
            rows = self._db.execute(sql, params).fetchall()
        else:
            # Build the ANN query for PostgreSQL / pgvector.
            threshold_clause = ""
            if threshold is not None:
                threshold_clause = f"AND (dc.embedding <=> '{vector_literal}'::vector) <= {threshold}"

            sql = text(
                f"""
                SELECT
                    dc.id                                               AS chunk_id,
                    dc.document_id,
                    dc.chunk_index,
                    dc.text_content,
                    dc.page_numbers,
                    (dc.embedding <=> '{vector_literal}'::vector)      AS cosine_distance
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE
                    d.workspace_id = :workspace_id
                    AND d.status   = 'ready'
                    AND dc.embedding IS NOT NULL
                    {doc_filter}
                    {threshold_clause}
                ORDER BY cosine_distance ASC
                LIMIT :top_k
                """
            )
            rows = self._db.execute(sql, params).fetchall()

        results: list[RetrievedChunk] = []
        for row in rows:
            raw_pages = row.page_numbers
            if isinstance(raw_pages, str):
                raw_pages = json.loads(raw_pages)

            results.append(
                RetrievedChunk(
                    chunk_id=uuid.UUID(str(row.chunk_id)),
                    document_id=uuid.UUID(str(row.document_id)),
                    chunk_index=row.chunk_index,
                    text_content=row.text_content,
                    page_numbers=raw_pages or [],
                    cosine_distance=float(row.cosine_distance),
                )
            )

        logger.info(
            f"Workspace {workspace_id}: query returned {len(results)} chunks "
            f"(top_k={k}, threshold={threshold})"
        )
        return results
