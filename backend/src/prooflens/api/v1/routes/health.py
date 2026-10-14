"""Health and readiness check endpoints."""

from typing import Any

from fastapi import APIRouter, Response, status

from prooflens.core.logging import get_logger
from prooflens.db.session import check_database_readiness

logger = get_logger("prooflens.api.health")
router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
def liveness_check() -> dict[str, str]:
    """Returns simple status indicating the API service is alive."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
def readiness_check(response: Response) -> dict[str, Any]:
    """
    Validates availability of external dependencies:
    - PostgreSQL connection
    - pgvector extension installed in the target database
    """
    try:
        checks = check_database_readiness()
        all_ok = all(state == "ok" for state in checks.values())

        if not all_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not_ready",
                "checks": checks,
            }

        return {
            "status": "ready",
            "checks": checks,
        }
    except Exception as exc:
        logger.error(f"Readiness check failed with exception: {exc}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "checks": {
                "database": "error",
                "vector_extension": "error",
            },
        }
