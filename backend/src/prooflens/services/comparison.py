"""Cross-document comparison service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from prooflens.core.exceptions import DocumentNotFoundError, InsufficientScopeError
from prooflens.core.logging import get_logger
from prooflens.db.models.document import Document
from prooflens.schemas.analysis import CitationItem
from prooflens.schemas.comparison import CompareRequest, CompareResponse, DocumentFinding
from prooflens.services.llm import LLMService, StubLLMService, get_llm_service
from prooflens.services.retrieval import RetrievalService

logger = get_logger("prooflens.services.comparison")


class ComparisonService:
    """Orchestrates cross-document comparison across 2+ documents."""

    def __init__(
        self,
        db: Session,
        retrieval: RetrievalService | None = None,
        llm: LLMService | StubLLMService | None = None,
    ) -> None:
        self._db = db
        self._retrieval = retrieval or RetrievalService(db)
        self._llm = llm or get_llm_service()

    def compare(
        self,
        workspace_id: uuid.UUID,
        req: CompareRequest,
    ) -> CompareResponse:
        """
        Compare two or more documents within a workspace along a topic or thesis.

        Args:
            workspace_id: The enclosing workspace.
            req: Target document IDs and comparison topic.

        Returns:
            CompareResponse with per-document findings, synthesis, and relationship classification.
        """
        if len(req.document_ids) < 2:
            raise InsufficientScopeError("At least two document IDs are required for comparison.")

        # Validate that documents exist, belong to workspace, and are not soft-deleted
        stmt = (
            select(Document)
            .where(
                Document.workspace_id == workspace_id,
                Document.id.in_(req.document_ids),
                Document.deleted_at.is_(None),
            )
        )
        docs = {d.id: d for d in self._db.scalars(stmt).all()}

        for doc_id in req.document_ids:
            if doc_id not in docs:
                raise DocumentNotFoundError(str(doc_id))

        # Retrieve relevant passages per document
        findings: list[DocumentFinding] = []
        doc_chunks_for_llm: dict[str, tuple[str, list[Any]]] = {}

        for doc_id in req.document_ids:
            doc = docs[doc_id]
            chunks = self._retrieval.search(
                workspace_id=workspace_id,
                query=req.topic,
                top_k=req.top_k_per_doc,
                document_id=doc_id,
            )
            doc_chunks_for_llm[str(doc_id)] = (doc.original_filename, chunks)

            citations = [
                CitationItem(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    page_numbers=c.page_numbers,
                    text_excerpt=c.text_content[:200] + ("…" if len(c.text_content) > 200 else ""),
                )
                for c in chunks
            ]
            key_points = (
                [
                    f"Evidence from {doc.original_filename} (page {', '.join(str(p) for p in c.page_numbers)}): {c.text_content[:120]}…"
                    for c in chunks
                ]
                if chunks
                else [f"No passages found directly addressing '{req.topic}' in this document."]
            )
            findings.append(
                DocumentFinding(
                    document_id=doc_id,
                    document_name=doc.original_filename,
                    key_points=key_points,
                    citations=citations,
                )
            )

        # Let the LLM synthesize cross-document findings
        llm_result = self._llm.compare(topic=req.topic, doc_chunks=doc_chunks_for_llm)

        logger.info(
            f"Comparison completed for workspace {workspace_id} across {len(req.document_ids)} documents. "
            f"Relationship: {llm_result.relationship}"
        )

        return CompareResponse(
            workspace_id=workspace_id,
            topic=req.topic,
            documents=findings,
            synthesis=llm_result.synthesis,
            relationship=llm_result.relationship,  # type: ignore[arg-type]
            model_used=llm_result.model_used,
        )
