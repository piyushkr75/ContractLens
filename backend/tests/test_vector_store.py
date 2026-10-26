import numpy as np
import pytest
from app.models.schemas import DocumentChunk
from app.services.vector_store import FaissInMemoryIndex


def create_dummy_chunk(chunk_id: str, doc_id: str, text: str, section: str = "General", page: int = 1):
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        contract_id=doc_id,
        filename=f"{doc_id}.pdf",
        chunk_index=0,
        text=text,
        start_char=0,
        end_char=len(text),
        page_number=page,
        section=section,
        section_title=section,
        char_count=len(text),
        word_count=len(text.split()),
    )


class TestFaissInMemoryIndex:
    """Tests for in-memory FAISS index with metadata mapping, filtering, and thresholding."""

    def test_add_chunks_and_metadata_mapping(self):
        index = FaissInMemoryIndex(dimension=4)
        c1 = create_dummy_chunk("c1", "doc1", "Indemnity clause text")
        c2 = create_dummy_chunk("c2", "doc1", "Termination clause text")

        vectors = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ], dtype="float32")

        index.add_chunks([c1, c2], vectors)

        assert index.total_vectors == 2
        assert index.get_chunk_by_vector_id(0).chunk_id == "c1"
        assert index.get_chunk_by_vector_id(1).chunk_id == "c2"

    def test_similarity_search_ranks_correctly(self):
        index = FaissInMemoryIndex(dimension=4)
        c1 = create_dummy_chunk("c1", "doc1", "Clause A text")
        c2 = create_dummy_chunk("c2", "doc1", "Clause B text")

        vectors = np.array([
            [1.0, 0.0, 0.0, 0.0],  # Aligned with query
            [0.0, 1.0, 0.0, 0.0],  # Orthogonal
        ], dtype="float32")

        index.add_chunks([c1, c2], vectors)

        query = np.array([1.0, 0.0, 0.0, 0.0], dtype="float32")
        results = index.search(query, top_k=2)

        assert len(results) == 2
        assert results[0].chunk_id == "c1"
        assert np.isclose(results[0].similarity_score, 1.0, atol=1e-5)
        assert results[1].chunk_id == "c2"
        assert np.isclose(results[1].similarity_score, 0.0, atol=1e-5)

    def test_per_session_document_filtering(self):
        """When searching with filter_document_id, only chunks from that document are returned."""
        index = FaissInMemoryIndex(dimension=4)
        chunk_doc_a = create_dummy_chunk("c_a", "doc_A", "Contract A text")
        chunk_doc_b = create_dummy_chunk("c_b", "doc_B", "Contract B text")

        # Give doc_B a higher alignment vector
        vectors = np.array([
            [0.5, 0.5, 0.0, 0.0],  # doc_A (score ~0.707)
            [1.0, 0.0, 0.0, 0.0],  # doc_B (score 1.0)
        ], dtype="float32")

        index.add_chunks([chunk_doc_a, chunk_doc_b], vectors)

        query = np.array([1.0, 0.0, 0.0, 0.0], dtype="float32")

        # Search filtered to doc_A only
        results = index.search(query, top_k=4, filter_document_id="doc_A")

        assert len(results) == 1
        assert results[0].chunk_id == "c_a"

    def test_similarity_threshold_filtering(self):
        """Citations below similarity_threshold must be discarded."""
        index = FaissInMemoryIndex(dimension=4)
        c1 = create_dummy_chunk("c1", "doc1", "High similarity")
        c2 = create_dummy_chunk("c2", "doc1", "Low similarity")

        vectors = np.array([
            [0.9, 0.1, 0.0, 0.0],
            [0.1, 0.9, 0.0, 0.0],
        ], dtype="float32")

        index.add_chunks([c1, c2], vectors)

        query = np.array([1.0, 0.0, 0.0, 0.0], dtype="float32")
        # With threshold 0.5, c2 should be discarded
        results = index.search(query, top_k=4, similarity_threshold=0.5)

        assert len(results) == 1
        assert results[0].chunk_id == "c1"

    def test_top_k_limits_output(self):
        index = FaissInMemoryIndex(dimension=4)
        chunks = [create_dummy_chunk(f"c{i}", "doc1", f"Chunk {i}") for i in range(10)]
        # All identical vectors
        vectors = np.array([[1.0, 0.0, 0.0, 0.0]] * 10, dtype="float32")
        index.add_chunks(chunks, vectors)

        query = np.array([1.0, 0.0, 0.0, 0.0], dtype="float32")
        results = index.search(query, top_k=3)

        assert len(results) == 3

    def test_clear_index(self):
        index = FaissInMemoryIndex(dimension=4)
        c = create_dummy_chunk("c1", "doc1", "Sample text")
        index.add_chunks([c], np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32"))

        assert index.total_vectors == 1
        index.clear()
        assert index.total_vectors == 0
        assert len(index.vector_id_to_chunk) == 0
