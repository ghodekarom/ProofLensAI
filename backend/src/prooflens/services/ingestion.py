"""Document ingestion and extraction pipeline service."""

import uuid
from datetime import UTC, datetime

from fastapi import BackgroundTasks
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from prooflens.core.config import get_settings
from prooflens.core.exceptions import (
    DuplicateDocumentError,
    WorkspaceNotFoundError,
)
from prooflens.core.logging import get_logger
from prooflens.core.security import validate_pdf_upload
from prooflens.db.models.chunk import DocumentChunk
from prooflens.db.models.document import Document
from prooflens.db.models.page import DocumentPage
from prooflens.db.models.workspace import Workspace
from prooflens.db.session import get_session_factory
from prooflens.domain.enums import DocumentStatus
from prooflens.services.pdf_extraction import get_pdf_extraction_service
from prooflens.services.vectorization import VectorizationService
from prooflens.storage.local_filesystem import get_storage_service

logger = get_logger("prooflens.services.ingestion")


def utcnow() -> datetime:
    return datetime.now(UTC)


class IngestionService:
    """Coordinates PDF upload validation, storage, and text extraction."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.storage = get_storage_service()
        self.extractor = get_pdf_extraction_service()
        self.settings = get_settings()

    def upload_document(
        self,
        workspace_id: uuid.UUID,
        filename: str,
        content: bytes,
        background_tasks: BackgroundTasks | None = None,
    ) -> Document:
        # Verify workspace exists
        if not self.db.scalar(select(Workspace.id).where(Workspace.id == workspace_id)):
            raise WorkspaceNotFoundError(str(workspace_id))

        # Validate file bytes and format
        sha256 = validate_pdf_upload(
            data=content,
            filename=filename,
            max_bytes=self.settings.MAX_UPLOAD_BYTES,
        )

        # Check for workspace-scoped duplicate
        existing = self.db.scalar(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.sha256 == sha256,
            )
        )
        if existing:
            if existing.status == DocumentStatus.FAILED.value:
                # Clean up previous failed upload so user can retry cleanly
                old_key = existing.storage_key
                self.db.delete(existing)
                self.db.commit()
                if old_key:
                    try:
                        self.storage.delete(old_key)
                    except Exception as e:
                        logger.warning(f"Failed to delete old storage file: {e}")
            else:
                raise DuplicateDocumentError(filename=filename, sha256=sha256)

        # Save to storage
        document_id = uuid.uuid4()
        storage_key = self.storage.save(content, str(document_id), filename)

        # Create document entity
        document = Document(
            id=document_id,
            workspace_id=workspace_id,
            original_filename=filename,
            content_type="application/pdf",
            size_bytes=len(content),
            sha256=sha256,
            storage_key=storage_key,
            status=DocumentStatus.QUEUED.value,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        logger.info(
            f"Uploaded document '{filename}' (id: {document.id}) in workspace {workspace_id}"
        )

        # Dispatch ingestion pipeline
        if background_tasks:
            background_tasks.add_task(self.process_document_pipeline, document.id)
        else:
            self.process_document_pipeline(document.id)
            self.db.refresh(document)

        return document

    @classmethod
    def process_document_pipeline(cls, document_id: uuid.UUID) -> None:
        """Background worker: extract pages, chunk, embed, and index."""
        session_factory = get_session_factory()
        storage = get_storage_service()
        extractor = get_pdf_extraction_service()
        settings = get_settings()

        with session_factory() as db:
            document = db.scalar(select(Document).where(Document.id == document_id))
            if not document:
                logger.error(f"Cannot process missing document {document_id}")
                return

            try:
                document.status = DocumentStatus.PROCESSING.value
                document.processing_started_at = utcnow()
                # Clean up any leftover pages/chunks from previous attempts to prevent duplicate key errors
                db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
                db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
                db.commit()

                # ── Step 1: Extract text pages ──────────────────────────────
                pdf_bytes = storage.read(document.storage_key)
                pages = extractor.extract_pages(
                    pdf_bytes=pdf_bytes,
                    max_pages=settings.MAX_PDF_PAGES,
                )

                # Persist extracted pages
                for p in pages:
                    page_record = DocumentPage(
                        document_id=document.id,
                        page_number=p.page_number,
                        text_content=p.text_content,
                        character_count=p.character_count,
                        extraction_status=p.extraction_status,
                        page_metadata=p.metadata,
                    )
                    db.add(page_record)

                document.page_count = len(pages)
                document.error_code = None
                document.error_message = None
                db.commit()

                logger.info(f"Extracted {len(pages)} pages from document {document_id}.")

                # ── Step 2: Chunk → Embed → Persist (advances to READY) ─────
                vectorizer = VectorizationService(db)
                vectorizer.vectorize_document(document_id)

            except Exception as exc:
                logger.exception(f"Ingestion failed for document {document_id}: {exc}")
                try:
                    db.rollback()
                    doc_retry = db.scalar(select(Document).where(Document.id == document_id))
                    if doc_retry:
                        doc_retry.status = DocumentStatus.FAILED.value
                        doc_retry.error_code = "INGESTION_ERROR"
                        doc_retry.error_message = str(exc)[:500]
                        db.commit()
                except Exception as inner:  # noqa: BLE001
                    logger.error(f"Failed to record error state for document {document_id}: {inner}")
