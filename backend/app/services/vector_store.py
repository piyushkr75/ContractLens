import logging
from typing import Dict, List, Optional, Sequence, Union
import faiss
import numpy as np
from app.models.schemas import CitationSource, DocumentChunk

logger = logging.getLogger(__name__)


class FaissInMemoryIndex:
    """
    High-performance in-memory vector index built on FAISS IndexFlatIP (cosine similarity).
    Maps continuous vector IDs to DocumentChunk metadata entirely in memory.
    Supports:
    - Per-session document filtering (filter_document_id, filter_document_ids)
    - Configurable top-k retrieval
    - Similarity threshold filtering (e.g. discard results with cosine score below threshold)
    - Zero vector persistence to disk
    """

    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        # Vector ID (0, 1, 2, ...) -> DocumentChunk
        self.vector_id_to_chunk: Dict[int, DocumentChunk] = {}
        self.chunks: List[DocumentChunk] = []

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: np.ndarray):
        """
        Adds document chunks and normalized embedding vectors to the FAISS index.
        Maintains an explicit vector_id mapping in memory.
        """
        if len(chunks) == 0:
            return

        if embeddings.shape[0] != len(chunks):
            raise ValueError(
                f"Embedding count ({embeddings.shape[0]}) does not match chunk count ({len(chunks)})"
            )

        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Vector dimension ({embeddings.shape[1]}) does not match index dimension ({self.dimension})"
            )

        # Ensure L2 normalization for exact cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        normalized_vectors = np.ascontiguousarray(embeddings / norms, dtype="float32")

        start_vector_id = self.index.ntotal
        self.index.add(normalized_vectors)

        for i, chunk in enumerate(chunks):
            v_id = start_vector_id + i
            self.vector_id_to_chunk[v_id] = chunk
            self.chunks.append(chunk)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 4,
        similarity_threshold: float = 0.0,
        filter_document_id: Optional[str] = None,
        filter_document_ids: Optional[Sequence[str]] = None,
    ) -> List[CitationSource]:
        """
        Performs cosine similarity search against the in-memory FAISS index.
        Filters candidate chunks by document ID and similarity threshold.
        """
        if self.index.ntotal == 0:
            return []

        # Ensure normalized 2D float32 vector
        q_norm = np.linalg.norm(query_vector)
        if q_norm > 0:
            query_vector = query_vector / q_norm

        query_2d = np.ascontiguousarray(query_vector.reshape(1, -1), dtype="float32")

        # Determine filter set if provided
        allowed_docs = None
        if filter_document_id:
            allowed_docs = {filter_document_id}
        elif filter_document_ids:
            allowed_docs = set(filter_document_ids)

        # If filtering, search a broader candidate window (up to total vectors)
        candidate_k = min(self.index.ntotal, max(top_k * 5, 25)) if allowed_docs else min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_2d, candidate_k)

        citations: List[CitationSource] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx not in self.vector_id_to_chunk:
                continue

            float_score = float(score)
            if float_score < similarity_threshold:
                continue

            chunk = self.vector_id_to_chunk[idx]

            # Apply per-session document filter
            chunk_doc_id = chunk.document_id or chunk.contract_id
            if allowed_docs and chunk_doc_id not in allowed_docs:
                continue

            citations.append(
                CitationSource(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id or chunk.contract_id,
                    filename=chunk.filename,
                    chunk_index=chunk.chunk_index,
                    section_title=chunk.section or chunk.section_title,
                    page_number=chunk.page_number,
                    snippet=chunk.text[:280] + ("..." if len(chunk.text) > 280 else ""),
                    similarity_score=float_score,
                    verified=True,
                )
            )

            if len(citations) >= top_k:
                break

        return citations

    def get_chunk_by_vector_id(self, vector_id: int) -> Optional[DocumentChunk]:
        """Retrieves raw DocumentChunk metadata by internal vector ID."""
        return self.vector_id_to_chunk.get(vector_id)

    def has_document(self, document_id: str) -> bool:
        """Checks if any chunk in the index belongs to the given document ID."""
        return any(
            (c.document_id == document_id or c.contract_id == document_id)
            for c in self.vector_id_to_chunk.values()
        )

    def clear(self):
        """Clears all vectors and metadata from memory."""
        self.index.reset()
        self.vector_id_to_chunk.clear()
        self.chunks.clear()

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal
