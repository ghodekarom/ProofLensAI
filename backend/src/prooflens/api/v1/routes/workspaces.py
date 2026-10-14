"""Workspace API routes."""

import uuid

from fastapi import APIRouter, Query, status

from prooflens.api.deps import DBSessionDep
from prooflens.schemas.workspaces import (
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceResponse,
)
from prooflens.services.workspaces import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(data: WorkspaceCreate, db: DBSessionDep) -> WorkspaceResponse:
    """Creates a new workspace."""
    service = WorkspaceService(db)
    return service.create(data)


@router.get("", response_model=WorkspaceListResponse)
def list_workspaces(
    db: DBSessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> WorkspaceListResponse:
    """Lists accessible workspaces."""
    service = WorkspaceService(db)
    items = service.list(limit=limit)
    return WorkspaceListResponse(items=items, next_cursor=None)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: uuid.UUID, db: DBSessionDep) -> WorkspaceResponse:
    """Retrieves a single workspace by ID."""
    service = WorkspaceService(db)
    return service.get(workspace_id)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(workspace_id: uuid.UUID, db: DBSessionDep) -> None:
    """Deletes a workspace and all its documents and files."""
    service = WorkspaceService(db)
    service.delete(workspace_id)
