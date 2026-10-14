"""Document Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    filename: str
    size_bytes: int
    status: str
    uploaded_at: datetime
    status_url: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    filename: str = Field(validation_alias="original_filename")
    size_bytes: int
    page_count: int | None = None
    chunk_count: int | None = None
    status: str
    error_code: str | None = None
    error_message: str | None = None
    uploaded_at: datetime
    processed_at: datetime | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    next_cursor: str | None = None


class DocumentPageResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    page_number: int
    text: str
    text_content: str | None = None
    character_count: int | None = None
    extraction_status: str


class BatchUploadItem(BaseModel):
    id: uuid.UUID
    filename: str
    status: str


class BatchUploadRejectedItem(BaseModel):
    filename: str
    error: dict[str, Any]


class BatchUploadResponse(BaseModel):
    items: list[BatchUploadItem]
    rejected: list[BatchUploadRejectedItem]
