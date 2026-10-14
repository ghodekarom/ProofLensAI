"""Document retrieval and management service."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from prooflens.core.exceptions import (
    DocumentNotFoundError,
    EntityNotFoundError,
    WorkspaceNotFoundError,
)
from prooflens.core.logging import get_logger
from prooflens.db.models.document import Document
from prooflens.db.models.page import DocumentPage
from prooflens.db.models.workspace import Workspace
from prooflens.storage.local_filesystem import get_storage_service

logger = get_logger("prooflens.services.documents")


class DocumentService:
    """Manages document metadata, inspection, and deletion."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.storage = get_storage_service()

    def list(
        self,
        workspace_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
    ) -> list[Document]:
        # Verify workspace exists
        if not self.db.scalar(select(Workspace.id).where(Workspace.id == workspace_id)):
            raise WorkspaceNotFoundError(str(workspace_id))

        stmt = select(Document).where(Document.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(Document.status == status)
        stmt = stmt.order_by(Document.uploaded_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get(self, workspace_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        stmt = select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
        document = self.db.scalar(stmt)
        if not document:
            raise DocumentNotFoundError(str(document_id))
        return document

    def get_page(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        page_number: int,
    ) -> DocumentPage:
        # Check document belongs to workspace
        self.get(workspace_id, document_id)

        stmt = select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_number == page_number,
        )
        page = self.db.scalar(stmt)
        if not page:
            raise EntityNotFoundError(
                f"Page {page_number} for document '{document_id}' not found.",
                code="PAGE_NOT_FOUND",
            )
        return page

    def delete(self, workspace_id: uuid.UUID, document_id: uuid.UUID) -> None:
        document = self.get(workspace_id, document_id)
        storage_key = document.storage_key

        # Cascade delete in database
        self.db.delete(document)
        self.db.commit()

        # Delete physical file from storage
        if storage_key:
            self.storage.delete(storage_key)

        logger.info(f"Deleted document {document_id} and storage file {storage_key}")
