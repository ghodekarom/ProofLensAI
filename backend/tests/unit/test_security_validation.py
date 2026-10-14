"""Unit tests for upload validation and security rules."""

import pytest

from prooflens.core.exceptions import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedMediaTypeError,
)
from prooflens.core.security import validate_pdf_upload


def test_validate_pdf_valid():
    sample_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    sha256 = validate_pdf_upload(sample_pdf_bytes, "valid_report.pdf", max_bytes=1000)
    assert len(sha256) == 64


def test_validate_pdf_empty_file():
    with pytest.raises(InvalidFileError, match="Uploaded file is empty"):
        validate_pdf_upload(b"", "empty.pdf", max_bytes=1000)


def test_validate_pdf_too_large():
    big_content = b"%PDF-" + b"0" * 2000
    with pytest.raises(FileTooLargeError):
        validate_pdf_upload(big_content, "large.pdf", max_bytes=500)


def test_validate_pdf_invalid_extension():
    sample_bytes = b"%PDF-1.4 header"
    with pytest.raises(UnsupportedMediaTypeError, match="Only PDF files are supported"):
        validate_pdf_upload(sample_bytes, "report.docx", max_bytes=1000)


def test_validate_pdf_missing_magic_bytes():
    fake_bytes = b"This is plain text with .pdf extension"
    with pytest.raises(InvalidFileError, match="does not contain a valid PDF signature"):
        validate_pdf_upload(fake_bytes, "fake.pdf", max_bytes=1000)
