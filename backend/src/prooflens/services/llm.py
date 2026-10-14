"""LLM-backed grounded analysis and proofreading service."""

from __future__ import annotations

import re
from dataclasses import dataclass

from google import genai
from google.genai import types as genai_types

from prooflens.core.config import get_settings
from prooflens.core.logging import get_logger
from prooflens.services.retrieval import RetrievedChunk

logger = get_logger("prooflens.services.llm")

# ── Prompts ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are ProofLens AI, an expert document analysis assistant.
Your job is to answer questions and analyse documents based ONLY on the
provided source passages. Do not use outside knowledge.

Do not include any page numbers, brackets, or citations in your response.

If the answer is not found in the passages, say:
"I could not find relevant information in the provided documents."
"""

QUERY_TEMPLATE = """\
<context>
{context_block}
</context>

<question>
{question}
</question>

Instructions:
- Answer concisely using ONLY the context above.
- Do not include page numbers, citations, or references in your text.
- If insufficient context, state so clearly.
"""


# ── Data classes ───────────────────────────────────────────────────────────────


@dataclass
class Citation:
    """A single page-level citation extracted from the LLM response."""

    chunk_id: str
    document_id: str
    page_numbers: list[int]
    text_excerpt: str


@dataclass
class AnalysisResult:
    """Full response from the grounded analysis."""

    answer: str
    citations: list[Citation]
    model_used: str
    chunks_used: int


@dataclass
class ComparisonResult:
    """Full response from multi-document comparison."""

    synthesis: str
    relationship: str
    model_used: str


# ── Service ────────────────────────────────────────────────────────────────────


class LLMService:
    """
    Grounded Q&A and document analysis backed by Gemini.

    Takes a user question and pre-retrieved context chunks, builds a
    structured prompt, calls the Gemini LLM, and returns the answer
    together with structured citation metadata.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = genai.Client(
            api_key=self._settings.GOOGLE_API_KEY,
            http_options=genai_types.HttpOptions(
                timeout=15000,
                retry_options=genai_types.HttpRetryOptions(attempts=1),
            ),
        )
        self._model = self._settings.LLM_MODEL
        logger.info(f"LLMService initialised (model={self._model})")

    def _generate_with_fallback(
        self,
        contents: list[Any],
        config: genai_types.GenerateContentConfig,
    ) -> tuple[str, str]:
        """
        Attempt generation on primary model; quickly fall back to alternative
        Gemini models if the primary model is experiencing high demand (503).
        """
        candidates: list[str] = [self._model]
        for fallback in (
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
        ):
            if fallback not in candidates:
                candidates.append(fallback)

        last_exc: Exception | None = None
        for model_name in candidates:
            try:
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                text = response.text or ""
                return text, model_name
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(
                    f"Model '{model_name}' encountered {exc.__class__.__name__}: {exc}. "
                    "Falling back to next available model..."
                )

        logger.error(f"All LLM candidate models failed: {last_exc}")
        raise RuntimeError(f"LLM request failed across all candidate models: {last_exc}") from last_exc

    def analyse(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        *,
        max_output_tokens: int | None = None,
    ) -> AnalysisResult:
        """
        Generate a grounded answer for ``question`` using ``chunks`` as context.

        Args:
            question: User's question or analysis prompt.
            chunks: Retrieved passages ordered by relevance.
            max_output_tokens: Override the default token limit.

        Returns:
            AnalysisResult with the answer text and structured citations.
        """
        if not chunks:
            return AnalysisResult(
                answer="I could not find relevant information in the provided documents.",
                citations=[],
                model_used=self._model,
                chunks_used=0,
            )

        context_block = self._build_context_block(chunks)
        prompt = QUERY_TEMPLATE.format(context_block=context_block, question=question)

        contents = [
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=prompt)],
            )
        ]
        config = genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=max_output_tokens or self._settings.LLM_MAX_OUTPUT_TOKENS,
            temperature=0.1,  # Low temperature for factual grounding
        )

        answer_text, model_used = self._generate_with_fallback(contents, config)
        clean_answer = re.sub(r"\s*\[Page\s+[\d,\s]+\]", "", answer_text).strip()

        citations = self._extract_citations(chunks)

        logger.info(
            f"LLM analysis complete: {len(clean_answer)} chars, "
            f"{len(chunks)} context chunks, {len(citations)} citations (model={model_used})"
        )

        return AnalysisResult(
            answer=clean_answer,
            citations=citations,
            model_used=model_used,
            chunks_used=len(chunks),
        )

    def compare(
        self,
        topic: str,
        doc_chunks: dict[str, tuple[str, list[RetrievedChunk]]],
    ) -> ComparisonResult:
        """Synthesize cross-document comparison and classify relationship."""
        has_any_chunks = any(bool(chunks) for _, chunks in doc_chunks.values())
        if not has_any_chunks:
            return ComparisonResult(
                synthesis=f"No relevant passages found across the selected documents for topic: '{topic}'.",
                relationship="not_comparable",
                model_used=self._model,
            )

        sections = []
        for doc_id, (doc_name, chunks) in doc_chunks.items():
            context = self._build_context_block(chunks) if chunks else "No relevant passages found."
            sections.append(f"Document: {doc_name} (ID: {doc_id})\n{context}")

        prompt = (
            f"Compare the following documents regarding topic: '{topic}'.\n\n"
            + "\n\n====================\n\n".join(sections)
            + "\n\nProvide a synthesis comparing their findings, and explicitly determine their relationship as one of: "
            "'supports', 'differs', 'apparent_contradiction', or 'not_comparable'."
        )

        contents = [genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])]
        config = genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
        )

        synthesis, model_used = self._generate_with_fallback(contents, config)

        relationship = "differs"
        lower = synthesis.lower()
        if "contradiction" in lower:
            relationship = "apparent_contradiction"
        elif "support" in lower or "agree" in lower:
            relationship = "supports"
        elif "not comparable" in lower or "insufficient" in lower:
            relationship = "not_comparable"

        return ComparisonResult(
            synthesis=synthesis,
            relationship=relationship,
            model_used=model_used,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _build_context_block(chunks: list[RetrievedChunk]) -> str:
        """Build a numbered passage block with page attribution for the prompt."""
        lines: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            pages_str = ", ".join(str(p) for p in chunk.page_numbers)
            lines.append(f"[Passage {i} | Page {pages_str}]\n{chunk.text_content}")
        return "\n\n---\n\n".join(lines)

    @staticmethod
    def _extract_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
        """Convert retrieved chunks into structured Citation objects."""
        return [
            Citation(
                chunk_id=str(chunk.chunk_id),
                document_id=str(chunk.document_id),
                page_numbers=chunk.page_numbers,
                text_excerpt=chunk.text_content[:200] + ("…" if len(chunk.text_content) > 200 else ""),
            )
            for chunk in chunks
        ]


def get_llm_service() -> LLMService:
    """Factory returning a configured LLMService instance."""
    return LLMService()


class StubLLMService:
    """Deterministic stub for tests that avoids any API calls."""

    def analyse(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        *,
        max_output_tokens: int | None = None,
    ) -> AnalysisResult:
        answer = f"[STUB] Answer to: {question}" if chunks else "No relevant content found."
        return AnalysisResult(
            answer=answer,
            citations=[
                Citation(
                    chunk_id=str(c.chunk_id),
                    document_id=str(c.document_id),
                    page_numbers=c.page_numbers,
                    text_excerpt=c.text_content[:50],
                )
                for c in chunks
            ],
            model_used="stub",
            chunks_used=len(chunks),
        )

    def compare(
        self,
        topic: str,
        doc_chunks: dict[str, tuple[str, list[RetrievedChunk]]],
    ) -> ComparisonResult:
        has_content = any(bool(chunks) for _, chunks in doc_chunks.values())
        if not has_content:
            return ComparisonResult(
                synthesis=f"[STUB] No content found for topic: {topic}",
                relationship="not_comparable",
                model_used="stub",
            )
        return ComparisonResult(
            synthesis=f"[STUB] Cross-document comparison synthesis for topic: {topic}",
            relationship="supports",
            model_used="stub",
        )
