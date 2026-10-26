import json
from unittest.mock import MagicMock, patch
import pytest

from app.models.schemas import CitationSource, EvidenceStatus
from app.services.llm_service import GeminiLLMService


def create_dummy_citation(chunk_id: str, text: str, section: str = "General", page: int = 1):
    return CitationSource(
        chunk_id=chunk_id,
        document_id="doc_123",
        filename="Commercial_Agreement.pdf",
        chunk_index=0,
        section_title=section,
        page_number=page,
        snippet=text,
        similarity_score=0.92,
        verified=True,
    )


class TestQuestionAnsweringQA:
    """Unit tests for ContractLens question answering, citation verification, and evidence evaluation."""

    @pytest.fixture
    def mock_gemini_service(self):
        with patch("app.services.llm_service.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            service = GeminiLLMService(api_key="mock_key")
            service._client = mock_client
            yield service, mock_client

    def test_fabricated_citations_are_rejected(self, mock_gemini_service):
        """
        When Gemini hallucinates or fabricates chunk IDs not present in retrieved evidence,
        the backend must reject them and record the issue in limitations.
        """
        service, mock_client = mock_gemini_service

        real_chunk_id = "real_chunk_abc"
        fabricated_chunk_id = "hallucinated_chunk_xyz_999"

        retrieved_citations = [
            create_dummy_citation(real_chunk_id, "In no event shall aggregate liability exceed $50,000.")
        ]

        # Mock Gemini response attempting to cite both real and fabricated IDs
        fake_llm_payload = {
            "answer": "Liability is capped at $50,000 according to the limitation clause.",
            "evidence_status": "SUFFICIENT",
            "conflicting_clauses": [],
            "limitations": [],
            "citations": [
                {"chunk_id": real_chunk_id, "quote": "$50,000", "reason": "Mentions liability cap"},
                {"chunk_id": fabricated_chunk_id, "quote": "fabricated", "reason": "hallucinated chunk"},
            ],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(fake_llm_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = service.answer_contract_question(
            contract_id="doc_123",
            query="What is the liability cap?",
            retrieved_citations=retrieved_citations,
        )

        assert response.evidence_status == EvidenceStatus.SUFFICIENT
        # The fabricated chunk MUST NOT be in verified citations
        cited_ids = [c.chunk_id for c in response.citations]
        assert real_chunk_id in cited_ids
        assert fabricated_chunk_id not in cited_ids
        # Limitation must report the attempted fabrication
        assert any("unverified chunk ID 'hallucinated_chunk_xyz_999'" in lim for lim in response.limitations)

    def test_missing_and_insufficient_evidence_abstention(self, mock_gemini_service):
        """
        When evidence is missing or insufficient, service abstains and returns INSUFFICIENT status.
        """
        service, mock_client = mock_gemini_service

        # 1. Zero FAISS evidence retrieved
        res_empty = service.answer_contract_question(
            contract_id="doc_123",
            query="What are the data breach notification timelines?",
            retrieved_citations=[],
        )
        assert res_empty.evidence_status == EvidenceStatus.INSUFFICIENT
        assert "insufficient information" in res_empty.response.lower()
        assert len(res_empty.citations) == 0

        # 2. Evidence exists, but does not answer the question (model abstains)
        retrieved_citations = [
            create_dummy_citation("c_payment", "Customer will pay invoices within thirty (30) days.")
        ]

        llm_payload = {
            "answer": "The contract excerpts provided do not contain information regarding dispute arbitration venues.",
            "evidence_status": "INSUFFICIENT",
            "conflicting_clauses": [],
            "limitations": ["No dispute resolution or governing forum terms in retrieved excerpts."],
            "citations": [],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(llm_payload)
        mock_client.models.generate_content.return_value = mock_resp

        res_insufficient = service.answer_contract_question(
            contract_id="doc_123",
            query="Where will arbitration take place?",
            retrieved_citations=retrieved_citations,
        )

        assert res_insufficient.evidence_status == EvidenceStatus.INSUFFICIENT
        assert "excerpts provided do not contain" in res_insufficient.response
        assert len(res_insufficient.citations) == 0

    def test_conflicting_clauses_detection(self, mock_gemini_service):
        """
        When contract excerpts contradict each other, service identifies conflicting clauses
        and marks evidence_status as CONFLICTING.
        """
        service, mock_client = mock_gemini_service

        chunk1 = create_dummy_citation("c_term_1", "Section 4.1: Customer may terminate immediately with 24 hours notice.")
        chunk2 = create_dummy_citation("c_term_2", "Section 9.3: Neither party may terminate without ninety (90) days prior notice.")

        retrieved_citations = [chunk1, chunk2]

        llm_payload = {
            "answer": "The contract contains conflicting termination notice requirements between Section 4.1 and Section 9.3.",
            "evidence_status": "CONFLICTING",
            "conflicting_clauses": [
                "Section 4.1 permits termination on 24 hours notice whereas Section 9.3 requires 90 days prior notice."
            ],
            "limitations": ["Ambiguity requires renegotiation to harmonize termination notice provisions."],
            "citations": [
                {"chunk_id": "c_term_1", "quote": "24 hours notice", "reason": "Short notice right"},
                {"chunk_id": "c_term_2", "quote": "ninety (90) days", "reason": "Long notice requirement"},
            ],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(llm_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = service.answer_contract_question(
            contract_id="doc_123",
            query="What is the notice period for contract termination?",
            retrieved_citations=retrieved_citations,
        )

        assert response.evidence_status == EvidenceStatus.CONFLICTING
        assert len(response.conflicting_clauses) == 1
        assert "24 hours notice" in response.conflicting_clauses[0]
        assert len(response.citations) == 2
        assert response.citations[0].verified is True
        assert response.citations[1].verified is True

    def test_invalid_json_fallback_handling(self, mock_gemini_service):
        """
        If Gemini returns unparseable text instead of strict JSON,
        service recovers gracefully and outputs a safe partial response.
        """
        service, mock_client = mock_gemini_service

        retrieved_citations = [
            create_dummy_citation("c_general", "The parties agree to Delaware jurisdiction.")
        ]

        mock_resp = MagicMock()
        mock_resp.text = "MALFORMED_NON_JSON_RESPONSE: According to the contract, Delaware governs."
        mock_client.models.generate_content.return_value = mock_resp

        response = service.answer_contract_question(
            contract_id="doc_123",
            query="What is the governing law?",
            retrieved_citations=retrieved_citations,
        )

        assert "Delaware" in response.response
        assert response.evidence_status in [EvidenceStatus.PARTIAL, EvidenceStatus.SUFFICIENT]
        assert len(response.citations) >= 1
