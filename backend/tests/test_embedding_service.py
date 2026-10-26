from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from app.services.embedding_service import GeminiEmbeddingService


class TestGeminiEmbeddingService:
    """Unit tests for GeminiEmbeddingService with mocked Google GenAI client."""

    @pytest.fixture
    def mock_genai_client(self):
        with patch("app.services.embedding_service.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            yield mock_client

    def test_fallback_embeddings_when_unconfigured(self):
        """When no API key is provided, service generates normalized fallback vectors."""
        service = GeminiEmbeddingService(api_key=None)
        texts = ["First clause regarding indemnity.", "Second clause regarding payment."]
        embeddings = service.get_embeddings(texts)

        assert embeddings.shape == (2, 768)
        assert embeddings.dtype == np.float32
        # Check L2 normalization
        norms = np.linalg.norm(embeddings, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)

    def test_query_embedding_uses_retrieval_query_task_type(self, mock_genai_client):
        """User queries must be embedded with RETRIEVAL_QUERY task type."""
        # Setup mock return
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1] * 768
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]
        mock_genai_client.models.embed_content.return_value = mock_response

        service = GeminiEmbeddingService(api_key="mock_key", dimension=768)
        service._client = mock_genai_client

        vec = service.get_query_embedding("What is the limitation of liability cap?")

        assert vec.shape == (768,)
        assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-5)

        # Inspect call args
        mock_genai_client.models.embed_content.assert_called_once()
        _, kwargs = mock_genai_client.models.embed_content.call_args
        assert kwargs["config"].task_type == "RETRIEVAL_QUERY"
        assert kwargs["config"].output_dimensionality == 768

    def test_document_embedding_uses_retrieval_document_and_batches(self, mock_genai_client):
        """Contract chunks must use RETRIEVAL_DOCUMENT task type and batching."""
        # 5 texts with batch_size=2 should result in 3 API calls
        texts = [f"Clause text chunk #{i}" for i in range(5)]

        def mock_embed(model, contents, config):
            resp = MagicMock()
            items = []
            for _ in contents:
                emb = MagicMock()
                emb.values = [0.05] * 768
                items.append(emb)
            resp.embeddings = items
            return resp

        mock_genai_client.models.embed_content.side_effect = mock_embed

        service = GeminiEmbeddingService(api_key="mock_key", dimension=768, batch_size=2)
        service._client = mock_genai_client

        embeddings = service.get_embeddings(texts, task_type="RETRIEVAL_DOCUMENT", title="MSA.pdf")

        assert embeddings.shape == (5, 768)
        assert mock_genai_client.models.embed_content.call_count == 3
        # Check that config was passed with title and RETRIEVAL_DOCUMENT
        first_call_config = mock_genai_client.models.embed_content.call_args_list[0][1]["config"]
        assert first_call_config.task_type == "RETRIEVAL_DOCUMENT"
        assert first_call_config.title == "MSA.pdf"

    def test_retry_on_transient_error(self, mock_genai_client):
        """Service retries on 429 ResourceExhausted or transient errors before succeeding."""
        mock_embedding = MagicMock()
        mock_embedding.values = [0.2] * 768
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]

        # Fail once with 429, then succeed
        mock_genai_client.models.embed_content.side_effect = [
            Exception("429 ResourceExhausted: Rate limit exceeded"),
            mock_response,
        ]

        service = GeminiEmbeddingService(
            api_key="mock_key",
            dimension=768,
            max_retries=2,
            initial_backoff=0.01,
        )
        service._client = mock_genai_client

        embeddings = service.get_embeddings(["Test sentence with retry"])

        assert embeddings.shape == (1, 768)
        assert mock_genai_client.models.embed_content.call_count == 2
