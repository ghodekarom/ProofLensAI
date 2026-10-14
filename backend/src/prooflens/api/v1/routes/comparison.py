"""Cross-document comparison route — POST /workspaces/{id}/compare."""

import uuid

from fastapi import APIRouter, status

from prooflens.api.deps import DBSessionDep
from prooflens.schemas.comparison import CompareRequest, CompareResponse
from prooflens.services.comparison import ComparisonService

router = APIRouter(prefix="/workspaces/{workspace_id}/compare", tags=["Comparison"])


@router.post("", response_model=CompareResponse, status_code=status.HTTP_200_OK)
def compare_documents(
    workspace_id: uuid.UUID,
    body: CompareRequest,
    db: DBSessionDep,
) -> CompareResponse:
    """
    Compare findings across two or more indexed documents within a workspace.

    Produces per-document evidence findings and an overarching synthesis with
    a relationship classification (supports, differs, apparent_contradiction, or not_comparable).
    """
    svc = ComparisonService(db)
    return svc.compare(workspace_id=workspace_id, req=body)
