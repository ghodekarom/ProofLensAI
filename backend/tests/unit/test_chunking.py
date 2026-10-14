"""Unit tests for ChunkingService."""

import pytest

from prooflens.services.chunking import ChunkingService


def make_pages(texts: list[str]) -> list[tuple[int, str]]:
    return [(i + 1, text) for i, text in enumerate(texts)]


class TestChunkingService:
    def test_basic_chunking_single_page(self) -> None:
        """A page with more words than chunk_size produces multiple chunks."""
        svc = ChunkingService(chunk_size=10, overlap=2)
        words = " ".join(f"word{i}" for i in range(25))
        pages = make_pages([words])
        chunks = svc.chunk_pages("doc-1", pages)

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.token_count <= 10
            assert chunk.page_numbers == [1]

    def test_chunk_indices_are_sequential(self) -> None:
        svc = ChunkingService(chunk_size=5, overlap=1)
        pages = make_pages(["a b c d e f g h i j"])
        chunks = svc.chunk_pages("doc-2", pages)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_overlap_causes_repeated_words(self) -> None:
        """With overlap=2 and chunk_size=4, consecutive chunks share 2 words."""
        svc = ChunkingService(chunk_size=4, overlap=2)
        pages = make_pages(["a b c d e f g h"])
        chunks = svc.chunk_pages("doc-3", pages)
        assert len(chunks) >= 2
        # Last 2 words of chunk[0] should appear at start of chunk[1]
        words_0 = chunks[0].text_content.split()
        words_1 = chunks[1].text_content.split()
        assert words_0[-2:] == words_1[:2]

    def test_cross_page_provenance(self) -> None:
        """A chunk that spans two pages records both page numbers."""
        # chunk_size large enough to merge pages, overlap=0 for simplicity
        svc = ChunkingService(chunk_size=20, overlap=0)
        pages = make_pages(["page one text", "page two text"])
        chunks = svc.chunk_pages("doc-4", pages)
        # All words from both pages fit in one chunk → page_numbers should include 1 and 2
        all_pages = set()
        for c in chunks:
            all_pages.update(c.page_numbers)
        assert 1 in all_pages
        assert 2 in all_pages

    def test_empty_pages_returns_no_chunks(self) -> None:
        svc = ChunkingService(chunk_size=10, overlap=2)
        chunks = svc.chunk_pages("doc-5", [])
        assert chunks == []

    def test_blank_page_text_is_skipped(self) -> None:
        svc = ChunkingService(chunk_size=10, overlap=2)
        pages = make_pages(["   ", "\t\n", "real content here"])
        chunks = svc.chunk_pages("doc-6", pages)
        assert len(chunks) >= 1
        assert all("real" in c.text_content for c in chunks)

    def test_invalid_overlap_raises(self) -> None:
        with pytest.raises(ValueError, match="Overlap"):
            ChunkingService(chunk_size=10, overlap=10)

    def test_single_word_document(self) -> None:
        svc = ChunkingService(chunk_size=10, overlap=2)
        pages = make_pages(["hello"])
        chunks = svc.chunk_pages("doc-7", pages)
        assert len(chunks) == 1
        assert chunks[0].text_content == "hello"
        assert chunks[0].token_count == 1
