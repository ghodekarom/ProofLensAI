"""API v1 master router."""

from fastapi import APIRouter

from prooflens.api.v1.routes import (
    analysis,
    comparison,
    documents,
    health,
    search,
    workspaces,
)

api_v1_router = APIRouter()

# Health & readiness
api_v1_router.include_router(health.router)

# Workspaces & Documents
api_v1_router.include_router(workspaces.router)
api_v1_router.include_router(documents.router)

# Semantic Search
api_v1_router.include_router(search.router)

# Grounded Analysis & Comparison
api_v1_router.include_router(analysis.router)
api_v1_router.include_router(comparison.router)

