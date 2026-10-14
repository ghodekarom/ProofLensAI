"""Pydantic schemas for document analysis (Q&A) endpoint."""

import uuid

from pydantic import BaseModel, Field


class AnalyseRequest(BaseModel):
    """POST body for the workspace analysis endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Question or analysis prompt to answer from workspace documents",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of context passages to retrieve before answering",
    )
    document_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional filter — restrict search to these document IDs",
    )


class CitationItem(BaseModel):
    """A single cited passage included in the answer."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    page_numbers: list[int]
    text_excerpt: str


class AnalyseResponse(BaseModel):
    """Full analysis response with answer and structured citations."""

    question: str
    workspace_id: uuid.UUID
    answer: str
    citations: list[CitationItem]
    model_used: str
    chunks_used: int
