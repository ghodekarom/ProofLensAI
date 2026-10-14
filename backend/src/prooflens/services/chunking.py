"""Page-aware token-based chunking service."""

from dataclasses import dataclass, field
from typing import Any

from prooflens.core.logging import get_logger

logger = get_logger("prooflens.services.chunking")


@dataclass
class DocumentChunk:
    """Represents a single bounded text chunk with full provenance."""

    document_id: str
    chunk_index: int
    text_content: str
    page_numbers: list[int]
    token_count: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _naive_token_count(text: str) -> int:
    """Approximate token count using whitespace splitting (no tokenizer dependency)."""
    return len(text.split())


class ChunkingService:
    """
    Produces bounded, overlapping text chunks from extracted page text.

    Chunking strategy:
    - Page text is iterated sequentially.
    - Chunks are built word-by-word to respect token boundaries.
    - When a chunk's token count reaches CHUNK_SIZE, it is committed and an
      overlapping window of CHUNK_OVERLAP tokens seeded into the next chunk.
    - Each chunk tracks which page(s) it spans.
    - A chunk that spans a page boundary stores ALL contributing page numbers.
    """

    def __init__(self, chunk_size: int = 800, overlap: int = 120) -> None:
        if overlap >= chunk_size:
            raise ValueError(f"Overlap ({overlap}) must be less than chunk_size ({chunk_size}).")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_pages(
        self,
        document_id: str,
        pages: list[tuple[int, str]],  # [(page_number, text_content), ...]
    ) -> list[DocumentChunk]:
        """
        Chunks extracted page text into bounded segments with page provenance.

        Args:
            document_id: Stable UUID string of the parent document.
            pages: List of (1-based page_number, extracted_text) tuples.

        Returns:
            Ordered list of DocumentChunk objects.
        """
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        # Aggregate all words with page-number tagging
        word_stream: list[tuple[str, int]] = []
        for page_number, text in pages:
            if not text.strip():
                continue
            for word in text.split():
                word_stream.append((word, page_number))

        if not word_stream:
            logger.warning(f"Document {document_id}: no extractable words found across all pages.")
            return []

        i = 0
        while i < len(word_stream):
            window_words: list[str] = []
            page_set: set[int] = set()
            start_word_idx = i

            # Build chunk up to chunk_size tokens
            while i < len(word_stream) and len(window_words) < self.chunk_size:
                word, pg = word_stream[i]
                window_words.append(word)
                page_set.add(pg)
                i += 1

            if not window_words:
                break

            chunk_text = " ".join(window_words)
            token_count = len(window_words)

            # Calculate approximate char offsets within the whole stream
            start_char = sum(len(w) + 1 for w, _ in word_stream[:start_word_idx])
            end_char = start_char + len(chunk_text)

            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    text_content=chunk_text,
                    page_numbers=sorted(page_set),
                    token_count=token_count,
                    start_char=start_char,
                    end_char=end_char,
                    metadata={"pages_spanned": len(page_set)},
                )
            )
            chunk_index += 1

            if i >= len(word_stream):
                break

            # Step back by overlap to seed the next chunk
            step_back = min(self.overlap, len(window_words))
            if step_back >= len(window_words):
                break
            i -= step_back

        logger.info(
            f"Document {document_id}: produced {len(chunks)} chunks "
            f"(chunk_size={self.chunk_size}, overlap={self.overlap})"
        )
        return chunks


_chunking_instance: ChunkingService | None = None


def get_chunking_service(chunk_size: int = 800, overlap: int = 120) -> ChunkingService:
    """Returns a singleton chunking service with configured parameters."""
    global _chunking_instance
    if _chunking_instance is None:
        _chunking_instance = ChunkingService(chunk_size=chunk_size, overlap=overlap)
    return _chunking_instance
