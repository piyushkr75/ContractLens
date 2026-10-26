import hashlib
import logging
import random
import time
from typing import List, Optional

import numpy as np
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingService:
    """
    Hosted embedding service using the official Google Gen AI Python SDK (from google import genai).
    Produces L2-normalized 768-dimensional float32 vectors for in-memory FAISS IndexFlatIP (cosine similarity).

    Features:
    - Official SDK: client.models.embed_content
    - Task-specific configurations: RETRIEVAL_DOCUMENT vs RETRIEVAL_QUERY
    - Batching (default batch_size=50) for large contracts
    - Exponential backoff retry logic for 429/ResourceExhausted and transient errors
    - Deterministic local fallback for testing without active billing key
    - Zero vector persistence to disk
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
        batch_size: int = 50,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ):
        self.dimension = dimension or settings.GEMINI_EMBEDDING_DIMENSION
        self.model = model or settings.GEMINI_EMBEDDING_MODEL
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self._client: Optional[genai.Client] = None

        key = api_key or settings.active_gemini_api_key
        if key:
            try:
                self._client = genai.Client(api_key=key)
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI Client: {e}")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def get_embeddings(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        title: Optional[str] = None,
    ) -> np.ndarray:
        """
        Embeds a list of texts in batches using Google Gen AI SDK.
        Applies exponential backoff retries and returns L2-normalized 2D float32 array.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")

        if self._client:
            try:
                return self._embed_with_retry_and_batching(texts, task_type=task_type, title=title)
            except Exception as e:
                logger.warning(
                    f"Gemini hosted embedding failed ({e}). Falling back to deterministic local embedding."
                )

        return self._generate_fallback_embeddings(texts)

    def get_query_embedding(self, query: str) -> np.ndarray:
        """
        Embeds a user query string using RETRIEVAL_QUERY task type.
        Returns a 1D float32 vector normalized to unit length.
        """
        vectors = self.get_embeddings([query], task_type="RETRIEVAL_QUERY")
        return vectors[0]

    def _embed_with_retry_and_batching(
        self,
        texts: List[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
        title: Optional[str] = None,
    ) -> np.ndarray:
        """Processes texts in batches with exponential backoff on transient errors."""
        all_embeddings: List[List[float]] = []

        # Divide into batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_vectors = self._call_embed_content_with_retry(batch, task_type=task_type, title=title)
            all_embeddings.extend(batch_vectors)

        arr = np.array(all_embeddings, dtype="float32")
        return self._normalize_l2(arr)

    def _call_embed_content_with_retry(
        self,
        batch: List[str],
        task_type: str,
        title: Optional[str] = None,
    ) -> List[List[float]]:
        """Invokes client.models.embed_content with exponential backoff retry loop."""
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self.dimension,
            title=title,
        )

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config=config,
                )
                return [e.values for e in response.embeddings]
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str
                is_transient = is_rate_limit or "503" in err_str or "timeout" in err_str or "connection" in err_str

                if is_transient and attempt < self.max_retries:
                    # Exponential backoff with jitter
                    backoff = (self.initial_backoff * (2 ** attempt)) + random.uniform(0.1, 0.5)
                    logger.warning(
                        f"Gemini API embedding attempt {attempt + 1} encountered transient error ({e}). "
                        f"Retrying in {backoff:.2f}s..."
                    )
                    time.sleep(backoff)
                else:
                    raise last_error

        raise last_error

    @staticmethod
    def _normalize_l2(vectors: np.ndarray) -> np.ndarray:
        """Normalizes vectors to unit length so inner-product equals cosine similarity."""
        if vectors.size == 0:
            return vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        return (vectors / norms).astype("float32")

    def _generate_fallback_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generates deterministic pseudo-semantic vectors normalized to unit length.
        Ensures local testing runs without crashes when API keys are not supplied.
        """
        vectors = []
        for text in texts:
            vec = np.zeros(self.dimension, dtype="float32")
            words = text.lower().split()
            for word in words:
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                sign = 1.0 if ((h >> 4) % 2 == 0) else -1.0
                vec[idx] += sign
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            else:
                vec[0] = 1.0
            vectors.append(vec)
        return np.array(vectors, dtype="float32")


embedding_service = GeminiEmbeddingService()
