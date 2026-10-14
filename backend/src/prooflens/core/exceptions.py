"""Domain and API exceptions for ProofLens AI."""

from typing import Any


class ProofLensException(Exception):
    """Base exception for all ProofLens application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundError(ProofLensException):
    """Raised when an entity (workspace, document, etc.) cannot be found."""

    def __init__(self, message: str, code: str = "NOT_FOUND", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code=code, status_code=404, details=details)


class WorkspaceNotFoundError(EntityNotFoundError):
    def __init__(self, workspace_id: str) -> None:
        super().__init__(
            message=f"Workspace with id '{workspace_id}' not found.",
            code="WORKSPACE_NOT_FOUND",
            details={"workspace_id": workspace_id},
        )


class DocumentNotFoundError(EntityNotFoundError):
    def __init__(self, document_id: str) -> None:
        super().__init__(
            message=f"Document with id '{document_id}' not found.",
            code="DOCUMENT_NOT_FOUND",
            details={"document_id": document_id},
        )


class InvalidFileError(ProofLensException):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, code="INVALID_FILE", status_code=400, details=details)


class FileTooLargeError(ProofLensException):
    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            message=f"File size ({size_bytes} bytes) exceeds maximum limit ({max_bytes} bytes).",
            code="FILE_TOO_LARGE",
            status_code=413,
            details={"size_bytes": size_bytes, "max_bytes": max_bytes},
        )


class UnsupportedMediaTypeError(ProofLensException):
    def __init__(self, message: str = "Only PDF files (.pdf) are supported.") -> None:
        super().__init__(message=message, code="UNSUPPORTED_MEDIA_TYPE", status_code=415)


class DuplicateDocumentError(ProofLensException):
    def __init__(self, filename: str, sha256: str) -> None:
        super().__init__(
            message=f"A document identical to '{filename}' already exists in this workspace.",
            code="DUPLICATE_DOCUMENT",
            status_code=409,
            details={"filename": filename, "sha256": sha256},
        )


class DocumentNotReadyError(ProofLensException):
    def __init__(self, document_id: str, status: str) -> None:
        super().__init__(
            message=f"Document '{document_id}' is not ready for retrieval (status: {status}).",
            code="DOCUMENT_NOT_READY",
            status_code=409,
            details={"document_id": document_id, "status": status},
        )


class InsufficientScopeError(ProofLensException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="INSUFFICIENT_DOCUMENT_SCOPE", status_code=422)


class AIProviderError(ProofLensException):
    def __init__(self, message: str, provider: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="AI_PROVIDER_ERROR",
            status_code=502,
            details={"provider": provider, **(details or {})},
        )


class DependencyUnavailableError(ProofLensException):
    def __init__(self, message: str, dependency: str) -> None:
        super().__init__(
            message=message,
            code="DEPENDENCY_UNAVAILABLE",
            status_code=503,
            details={"dependency": dependency},
        )
