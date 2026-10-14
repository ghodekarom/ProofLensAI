"""Pydantic schemas for semantic search request and response."""

import uuid

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """POST body for the workspace search endpoint."""

    query: str = Field(..., min_length=1, max_length=2000, description="Free-text search query")
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of results to return (default: server setting)",
    )
    distance_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Maximum cosine distance to include (0 = identical, 2 = opposite)",
    )


class SearchResultItem(BaseModel):
    """A single ranked passage from the semantic index."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text_content: str
    page_numbers: list[int]
    cosine_distance: float
    cosine_similarity: float

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    """Top-level search response envelope."""

    query: str
    workspace_id: uuid.UUID
    total_results: int
    results: list[SearchResultItem]
