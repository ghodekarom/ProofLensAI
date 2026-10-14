"""Pydantic schemas for cross-document comparison."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from prooflens.schemas.analysis import CitationItem

ComparisonRelationship = Literal[
    "supports",
    "differs",
    "apparent_contradiction",
    "not_comparable",
]


class CompareRequest(BaseModel):
    """Request payload to compare multiple documents on a topic."""

    document_ids: list[uuid.UUID] = Field(
        ...,
        min_length=2,
        description="At least two document UUIDs to compare",
    )
    topic: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Topic, thesis, or question to compare across documents",
    )
    top_k_per_doc: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Passages to retrieve per document",
    )


class DocumentFinding(BaseModel):
    """Summary and evidence for a specific document on the topic."""

    document_id: uuid.UUID
    document_name: str
    key_points: list[str]
    citations: list[CitationItem]


class CompareResponse(BaseModel):
    """Cross-document comparison analysis with provenance."""

    workspace_id: uuid.UUID
    topic: str
    documents: list[DocumentFinding]
    synthesis: str
    relationship: ComparisonRelationship
    model_used: str
