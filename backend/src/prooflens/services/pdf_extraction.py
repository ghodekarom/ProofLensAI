"""Page-aware PDF text extraction service using PyMuPDF."""

from dataclasses import dataclass
from typing import Any

import fitz  # PyMuPDF

from prooflens.core.exceptions import InvalidFileError
from prooflens.core.logging import get_logger
from prooflens.domain.enums import PageExtractionStatus

logger = get_logger("prooflens.services.pdf_extraction")


@dataclass
class ExtractedPage:
    """Represents text and metadata extracted from a single PDF page."""
    page_number: int  # 1-based
    text_content: str
    character_count: int
    extraction_status: str
    metadata: dict[str, Any]


class PDFExtractionService:
    """Extracts text and provenance metadata from PDF files."""

    def __init__(self, min_chars_per_page: int = 15) -> None:
        self.min_chars_per_page = min_chars_per_page

    def extract_pages(self, pdf_bytes: bytes, max_pages: int = 500) -> list[ExtractedPage]:
        """
        Parses PDF bytes, validates encryption and page bounds,
        and extracts text page-by-page preserving 1-based page numbers.
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            raise InvalidFileError(f"Failed to parse PDF document: {exc}") from exc

        try:
            if doc.is_encrypted:
                raise InvalidFileError("Encrypted or password-protected PDFs are not supported.")

            total_pages = doc.page_count
            if total_pages == 0:
                raise InvalidFileError("The uploaded PDF contains zero pages.")

            if total_pages > max_pages:
                raise InvalidFileError(
                    f"PDF contains {total_pages} pages, which exceeds the limit of {max_pages} pages."
                )

            extracted_pages: list[ExtractedPage] = []

            for index in range(total_pages):
                page = doc.load_page(index)
                page_number = index + 1  # Strictly 1-based page numbering
                raw_text = page.get_text("text") or ""
                clean_text = raw_text.strip()
                char_count = len(clean_text)

                if char_count >= self.min_chars_per_page:
                    status = PageExtractionStatus.EXTRACTED.value
                elif char_count == 0:
                    status = PageExtractionStatus.EMPTY.value
                else:
                    # Very few characters (might be image-only / scanned)
                    status = PageExtractionStatus.UNSUPPORTED.value

                page_meta = {
                    "width": round(page.rect.width, 2),
                    "height": round(page.rect.height, 2),
                    "rotation": page.rotation,
                    "is_image_only": char_count < self.min_chars_per_page,
                }

                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text_content=clean_text,
                        character_count=char_count,
                        extraction_status=status,
                        metadata=page_meta,
                    )
                )

            logger.info(f"Successfully extracted {len(extracted_pages)} pages from PDF")
            return extracted_pages
        finally:
            doc.close()


_extractor_instance = None


def get_pdf_extraction_service() -> PDFExtractionService:
    """Returns singleton PDF extraction service."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = PDFExtractionService()
    return _extractor_instance
