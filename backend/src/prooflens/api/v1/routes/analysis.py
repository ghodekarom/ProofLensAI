"""Document analysis (grounded Q&A) route — POST /workspaces/{id}/analyse."""

import uuid

from fastapi import APIRouter, status

from prooflens.api.deps import DBSessionDep
from prooflens.schemas.analysis import AnalyseRequest, AnalyseResponse, CitationItem
from prooflens.services.llm import get_llm_service
from prooflens.services.retrieval import RetrievalService

router = APIRouter(prefix="/workspaces/{workspace_id}/analyse", tags=["Analysis"])


@router.post("", response_model=AnalyseResponse, status_code=status.HTTP_200_OK)
def analyse_workspace(
    workspace_id: uuid.UUID,
    body: AnalyseRequest,
    db: DBSessionDep,
) -> AnalyseResponse:
    """
    Answer a question grounded in the workspace's indexed documents.

    Workflow:
    1. Semantically retrieve the top-K most relevant passages.
    2. Pass them as context to the Gemini LLM.
    3. Return the answer with page-level citations.
    """
    # ── Step 1: Retrieve relevant passages ─────────────────────────────────────
    retrieval_svc = RetrievalService(db)
    chunks = retrieval_svc.search(
        workspace_id=workspace_id,
        query=body.question,
        top_k=body.top_k,
    )

    # ── Step 2: Ground the LLM on retrieved passages ────────────────────────────
    llm = get_llm_service()
    result = llm.analyse(question=body.question, chunks=chunks)

    # ── Step 3: Build response ──────────────────────────────────────────────────
    citations = [
        CitationItem(
            chunk_id=uuid.UUID(c.chunk_id),
            document_id=uuid.UUID(c.document_id),
            page_numbers=c.page_numbers,
            text_excerpt=c.text_excerpt,
        )
        for c in result.citations
    ]

    return AnalyseResponse(
        question=body.question,
        workspace_id=workspace_id,
        answer=result.answer,
        citations=citations,
        model_used=result.model_used,
        chunks_used=result.chunks_used,
    )
