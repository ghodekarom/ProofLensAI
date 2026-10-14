"""Unit tests for PyMuPDF page-aware PDF text extraction."""

import fitz  # PyMuPDF
import pytest

from prooflens.core.exceptions import InvalidFileError
from prooflens.domain.enums import PageExtractionStatus
from prooflens.services.pdf_extraction import PDFExtractionService


def create_in_memory_pdf(pages_text: list[str]) -> bytes:
    """Creates a temporary multi-page PDF in memory using PyMuPDF."""
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842)  # A4 size
        if text:
            page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_extract_pages_with_valid_text():
    pages_content = [
        "First page content with important findings about artificial intelligence.",
        "Second page discussing technical architecture and evaluation methodologies.",
    ]
    pdf_bytes = create_in_memory_pdf(pages_content)
    service = PDFExtractionService()

    extracted = service.extract_pages(pdf_bytes)

    assert len(extracted) == 2
    # Verify 1-based page numbering
    assert extracted[0].page_number == 1
    assert "First page content" in extracted[0].text_content
    assert extracted[0].extraction_status == PageExtractionStatus.EXTRACTED.value

    assert extracted[1].page_number == 2
    assert "Second page discussing" in extracted[1].text_content
    assert extracted[1].extraction_status == PageExtractionStatus.EXTRACTED.value


def test_extract_pages_detects_empty_page():
    pages_content = [
        "Normal page content with sufficient characters.",
        "",  # Completely empty page
    ]
    pdf_bytes = create_in_memory_pdf(pages_content)
    service = PDFExtractionService()

    extracted = service.extract_pages(pdf_bytes)

    assert len(extracted) == 2
    assert extracted[0].page_number == 1
    assert extracted[0].extraction_status == PageExtractionStatus.EXTRACTED.value

    assert extracted[1].page_number == 2
    assert extracted[1].character_count == 0
    assert extracted[1].extraction_status == PageExtractionStatus.EMPTY.value
    assert extracted[1].metadata["is_image_only"] is True


def test_extract_pages_rejects_corrupted_data():
    service = PDFExtractionService()
    with pytest.raises(InvalidFileError, match="Failed to parse PDF document"):
        service.extract_pages(b"not_a_real_pdf_stream_data")


def test_extract_pages_exceeding_page_limit():
    pages_content = ["Page 1", "Page 2", "Page 3"]
    pdf_bytes = create_in_memory_pdf(pages_content)
    service = PDFExtractionService()

    with pytest.raises(InvalidFileError, match="exceeds the limit of 2 pages"):
        service.extract_pages(pdf_bytes, max_pages=2)
