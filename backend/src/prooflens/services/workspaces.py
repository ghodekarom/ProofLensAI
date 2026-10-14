"""Workspace business logic service."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from prooflens.core.exceptions import WorkspaceNotFoundError
from prooflens.core.logging import get_logger
from prooflens.db.models.document import Document
from prooflens.db.models.workspace import Workspace
from prooflens.schemas.workspaces import WorkspaceCreate
from prooflens.storage.local_filesystem import get_storage_service

logger = get_logger("prooflens.services.workspaces")


class WorkspaceService:
    """Manages workspace lifecycle."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.storage = get_storage_service()

    def create(self, data: WorkspaceCreate) -> Workspace:
        workspace = Workspace(
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
        )
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        logger.info(f"Created workspace '{workspace.name}' (id: {workspace.id})")
        return workspace

    def list(self, limit: int = 20) -> list[Workspace]:
        stmt = select(Workspace).order_by(Workspace.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get(self, workspace_id: uuid.UUID) -> Workspace:
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        workspace = self.db.scalar(stmt)
        if not workspace:
            raise WorkspaceNotFoundError(str(workspace_id))
        return workspace

    def delete(self, workspace_id: uuid.UUID) -> None:
        workspace = self.get(workspace_id)

        # Retrieve documents to clean up stored physical files
        stmt = select(Document).where(Document.workspace_id == workspace_id)
        documents = self.db.scalars(stmt).all()
        for doc in documents:
            if doc.storage_key:
                self.storage.delete(doc.storage_key)

        self.db.delete(workspace)
        self.db.commit()
        logger.info(f"Deleted workspace {workspace_id} and all associated files.")
