"""Semantic search route — POST /workspaces/{workspace_id}/search."""

import uuid

from fastapi import APIRouter, status

from prooflens.api.deps import DBSessionDep
from prooflens.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from prooflens.services.retrieval import RetrievalService

router = APIRouter(prefix="/workspaces/{workspace_id}/search", tags=["Search"])


@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
def search_workspace(
    workspace_id: uuid.UUID,
    body: SearchRequest,
    db: DBSessionDep,
) -> SearchResponse:
    """
    Semantically search all ready documents in a workspace.

    Returns the top-K most similar passages ordered by ascending cosine distance.
    Each result includes the contributing page numbers for citation rendering.
    """
    service = RetrievalService(db)
    retrieved = service.search(
        workspace_id=workspace_id,
        query=body.query,
        top_k=body.top_k,
        distance_threshold=body.distance_threshold,
    )

    items = [
        SearchResultItem(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            chunk_index=r.chunk_index,
            text_content=r.text_content,
            page_numbers=r.page_numbers,
            cosine_distance=r.cosine_distance,
            cosine_similarity=r.cosine_similarity,
        )
        for r in retrieved
    ]

    return SearchResponse(
        query=body.query,
        workspace_id=workspace_id,
        total_results=len(items),
        results=items,
    )
