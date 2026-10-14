"""Document upload, status tracking, and page inspection routes."""

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Query,
    UploadFile,
    status,
)

from prooflens.api.deps import DBSessionDep
from prooflens.core.exceptions import InvalidFileError
from prooflens.schemas.documents import (
    BatchUploadItem,
    BatchUploadRejectedItem,
    BatchUploadResponse,
    DocumentListResponse,
    DocumentPageResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from prooflens.services.documents import DocumentService
from prooflens.services.ingestion import IngestionService

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["Documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    workspace_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    file: Annotated[UploadFile, File()],
) -> DocumentUploadResponse:
    """Uploads a single PDF document and begins asynchronous text extraction."""
    if not file.filename:
        raise InvalidFileError("Uploaded file must have a filename.")

    content = await file.read()
    service = IngestionService(db)
    document = service.upload_document(
        workspace_id=workspace_id,
        filename=file.filename,
        content=content,
        background_tasks=background_tasks,
    )

    return DocumentUploadResponse(
        id=document.id,
        workspace_id=document.workspace_id,
        filename=document.original_filename,
        size_bytes=document.size_bytes,
        status=document.status,
        uploaded_at=document.uploaded_at,
        status_url=f"/api/v1/workspaces/{workspace_id}/documents/{document.id}",
    )


@router.post("/batch", response_model=BatchUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_documents_batch(
    workspace_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    files: Annotated[list[UploadFile], File()],
) -> BatchUploadResponse:
    """Uploads multiple PDFs in a single request with per-file result tracking."""
    service = IngestionService(db)
    items: list[BatchUploadItem] = []
    rejected: list[BatchUploadRejectedItem] = []

    for f in files:
        filename = f.filename or "unknown.pdf"
        try:
            content = await f.read()
            doc = service.upload_document(
                workspace_id=workspace_id,
                filename=filename,
                content=content,
                background_tasks=background_tasks,
            )
            items.append(BatchUploadItem(id=doc.id, filename=filename, status=doc.status))
        except Exception as exc:
            code = getattr(exc, "code", "UPLOAD_FAILED")
            message = getattr(exc, "message", str(exc))
            rejected.append(
                BatchUploadRejectedItem(
                    filename=filename,
                    error={"code": code, "message": message},
                )
            )

    return BatchUploadResponse(items=items, rejected=rejected)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    workspace_id: uuid.UUID,
    db: DBSessionDep,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> DocumentListResponse:
    """Lists documents in a workspace."""
    service = DocumentService(db)
    docs = service.list(workspace_id=workspace_id, status=status, limit=limit)
    return DocumentListResponse(items=docs, next_cursor=None)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    db: DBSessionDep,
) -> DocumentResponse:
    """Retrieves document status and metadata."""
    service = DocumentService(db)
    return service.get(workspace_id, document_id)


@router.get("/{document_id}/pages/{page_number}", response_model=DocumentPageResponse)
def get_document_page(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    page_number: int,
    db: DBSessionDep,
) -> DocumentPageResponse:
    """Inspects extracted text for a specific page."""
    service = DocumentService(db)
    doc = service.get(workspace_id, document_id)
    page = service.get_page(workspace_id, document_id, page_number)

    return DocumentPageResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        page_number=page.page_number,
        text=page.text_content,
        text_content=page.text_content,
        character_count=page.character_count or len(page.text_content),
        extraction_status=page.extraction_status,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    db: DBSessionDep,
) -> None:
    """Deletes a document and its stored physical file."""
    service = DocumentService(db)
    service.delete(workspace_id, document_id)
