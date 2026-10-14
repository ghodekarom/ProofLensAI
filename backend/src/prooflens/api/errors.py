"""Standard API error responses and exception handlers."""

import uuid
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from prooflens.core.exceptions import ProofLensException
from prooflens.core.logging import get_logger

logger = get_logger("prooflens.api.errors")


def make_error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Builds a standardized error envelope JSON response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details or {},
            }
        },
    )


async def prooflens_exception_handler(request: Request, exc: ProofLensException) -> JSONResponse:
    """Handles domain-specific ProofLens exceptions."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.warning(
        f"Domain exception [{exc.code}] on {request.method} {request.url.path}: {exc.message}",
        extra={"request_id": request_id, "status_code": exc.status_code},
    )
    return make_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=request_id,
        details=exc.details,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic / FastAPI request validation errors."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    errors_summary = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors_summary.append({"location": loc, "message": msg})

    logger.info(
        f"Validation error on {request.method} {request.url.path}",
        extra={"request_id": request_id, "errors": errors_summary},
    )
    return make_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="VALIDATION_ERROR",
        message="The request payload failed validation.",
        request_id=request_id,
        details={"validation_errors": errors_summary},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles Starlette / FastAPI HTTP exceptions."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    code_map = {
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        415: "UNSUPPORTED_MEDIA_TYPE",
        500: "INTERNAL_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return make_error_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail),
        request_id=request_id,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches all unhandled exceptions and prevents stack trace leakage."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(
        f"Unhandled server error on {request.method} {request.url.path}",
        exc_info=exc,
        extra={"request_id": request_id},
    )
    return make_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message="An unexpected internal server error occurred. Please try again later.",
        request_id=request_id,
    )
