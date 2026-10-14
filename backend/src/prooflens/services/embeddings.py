"""Gemini Embedding provider with retry logic and batching."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from google import genai
from google.genai import types as genai_types

from prooflens.core.config import get_settings
from prooflens.core.logging import get_logger

logger = get_logger("prooflens.services.embeddings")


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the output vector dimensionality."""

    @abstractmethod
    def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """
        Produce embedding vectors for a list of texts.

        Args:
            texts: Non-empty list of text strings.
            task_type: Embedding task type ("RETRIEVAL_DOCUMENT" or "RETRIEVAL_QUERY").

        Returns:
            Parallel list of float vectors, each of length ``self.dimensions``.
        """


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Production embedding provider backed by the Gemini Embedding API.

    - Model: ``gemini-embedding-2`` (768 dimensions).
    - Texts are embedded in configurable batch sizes to avoid request timeouts.
    - Exponential backoff on transient API errors (up to MAX_RETRIES).
    """

    MAX_RETRIES = 3
    INITIAL_BACKOFF_S = 1.0
    BACKOFF_MULTIPLIER = 2.0

    def __init__(self, batch_size: int = 32) -> None:
        settings = get_settings()
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = 768
        self._batch_size = batch_size
        self._client = genai.Client(
            api_key=settings.GOOGLE_API_KEY,
            http_options=genai_types.HttpOptions(timeout=15000),
        )
        logger.info(f"GeminiEmbeddingProvider initialised (model={self._model}, dims={self._dimensions})")

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        if not texts:
            raise ValueError("embed_texts requires at least one text.")

        all_vectors: list[list[float]] = []
        for batch_start in range(0, len(texts), self._batch_size):
            batch = texts[batch_start : batch_start + self._batch_size]
            vectors = self._embed_batch_with_retry(batch, task_type=task_type)
            all_vectors.extend(vectors)

        return all_vectors

    def _embed_batch_with_retry(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        backoff = self.INITIAL_BACKOFF_S
        last_error: Exception | None = None

        contents = [
            genai_types.Content(parts=[genai_types.Part.from_text(text=t.strip() or " ")])
            for t in texts
        ]

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self._client.models.embed_content(
                    model=self._model,
                    contents=contents,
                    config=genai_types.EmbedContentConfig(
                        output_dimensionality=self._dimensions,
                        task_type=task_type,
                    ),
                )
                embeddings = [list(emb.values) for emb in response.embeddings]
                if len(embeddings) != len(texts):
                    raise RuntimeError(
                        f"Embedding provider returned {len(embeddings)} vectors for {len(texts)} input chunks."
                    )
                return embeddings
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    logger.warning(
                        f"Embedding API error (attempt {attempt}/{self.MAX_RETRIES}): {exc}. "
                        f"Retrying in {backoff:.1f}s …"
                    )
                    time.sleep(backoff)
                    backoff *= self.BACKOFF_MULTIPLIER

        raise RuntimeError(f"Embedding failed after {self.MAX_RETRIES} attempts: {last_error}") from last_error


class StubEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic stub provider for testing and CI environments.

    Returns zero vectors of the configured dimensionality without making
    any network calls.
    """

    def __init__(self, dims: int = 768) -> None:
        self._dims = dims

    @property
    def dimensions(self) -> int:
        return self._dims

    def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        return [[0.0] * self._dims for _ in texts]


def get_embedding_provider() -> EmbeddingProvider:
    """
    Factory returning the appropriate embedding provider.

    Uses the real Gemini provider in production and the stub in test mode.
    """
    settings = get_settings()
    if settings.TESTING:
        return StubEmbeddingProvider()
    return GeminiEmbeddingProvider()
