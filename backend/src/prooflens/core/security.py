"""Security, validation, and file integrity utilities."""

import hashlib
from pathlib import Path

from prooflens.core.exceptions import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedMediaTypeError,
)


def compute_sha256(data: bytes) -> str:
    """Computes SHA-256 hex digest for given bytes."""
    return hashlib.sha256(data).hexdigest()


def validate_pdf_upload(data: bytes, filename: str, max_bytes: int) -> str:
    """
    Validates uploaded file for:
    - Non-empty byte content
    - Maximum size cap
    - .pdf extension
    - %PDF magic bytes signature
    Returns SHA-256 hash on success.
    """
    size_bytes = len(data)
    if size_bytes == 0:
        raise InvalidFileError("Uploaded file is empty.")

    if size_bytes > max_bytes:
        raise FileTooLargeError(size_bytes=size_bytes, max_bytes=max_bytes)

    # Validate extension
    extension = Path(filename).suffix.lower()
    if extension != ".pdf":
        raise UnsupportedMediaTypeError(
            f"File '{filename}' has unsupported extension '{extension}'. Only PDF files are supported."
        )

    # Validate magic bytes: PDFs must start with %PDF- (0x25 0x50 0x44 0x46)
    if not data.startswith(b"%PDF-"):
        raise InvalidFileError(
            f"File '{filename}' does not contain a valid PDF signature header."
        )

    return compute_sha256(data)
