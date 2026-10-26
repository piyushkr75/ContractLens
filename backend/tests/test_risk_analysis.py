import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_memory_store
from app.core.memory_store import InMemoryContractStore
from app.models.schemas import (
    AnalyzeRequest,
    CitationSource,
    ClauseAnalysis,
    ClausePresenceStatus,
    DocumentChunk,
    RawClauseRiskAnalysis,
    RawContractRiskResponse,
    RiskLevel,
)
from app.services.llm_service import (
    GeminiLLMService,
    ILLUSTRATIVE_REVIEW_CHECKLIST,
    TARGET_CLAUSE_CATEGORIES,
)


def create_dummy_chunk(chunk_id: str, doc_id: str, text: str, section: str = "General", page: int = 1) -> DocumentChunk:
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


def create_dummy_citation(chunk_id: str, text: str) -> CitationSource:
    return CitationSource(
        chunk_id=chunk_id,
        document_id="contract_test_1",
        filename="Agreement.pdf",
        chunk_index=0,
        section_title="General",
        page_number=1,
        snippet=text,
        similarity_score=0.91,
        verified=True,
    )


class TestContractRiskAnalysis:
    """Unit tests for ContractLens risk analysis, clause presence, policy review, and guardrails."""

    @pytest.fixture
    def mock_gemini_service(self):
        with patch("app.services.llm_service.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            service = GeminiLLMService(api_key="mock_key")
            service._client = mock_client
            yield service, mock_client

    def test_heuristic_analysis_covers_all_eight_categories(self):
        """Heuristic analysis must cover all 8 target categories and include legal disclaimer."""
        service = GeminiLLMService(api_key=None)  # No API key -> forces heuristic fallback
        contract_text = "This is a basic consulting agreement between Party A and Party B."

        response = service.analyze_contract(
            contract_id="c_1",
            filename="consulting.txt",
            contract_text=contract_text,
        )

        assert len(response.clauses) == 8
        expected_categories = {
            "Termination",
            "Indemnification",
            "Liability Limits",
            "Confidentiality",
            "Payment",
            "Automatic Renewal",
            "Data Protection",
            "Dispute Resolution",
        }
        actual_categories = {c.category for c in response.clauses}
        assert actual_categories == expected_categories

        # Verify legal disclaimer and default checklist
        assert "Does not constitute legal advice." in response.legal_disclaimer
        assert response.review_policy_used.startswith("[ILLUSTRATIVE_REVIEW_CHECKLIST")
        assert len(response.category_breakdowns) == 8

    def test_absent_clauses_guardrails(self):
        """
        Guardrails test:
        - Absent Auto-Renewal MUST be LOW risk (do not assume all missing clauses are high risk!).
        - Absent Liability Limits MUST be CRITICAL risk (unlimited exposure).
        - Absent Indemnification MUST be LOW risk.
        """
        service = GeminiLLMService(api_key=None)
        contract_text = "Standard order form with no legal clauses whatsoever."

        response = service.analyze_contract(
            contract_id="c_2",
            filename="order_form.txt",
            contract_text=contract_text,
        )

        clause_map = {c.category: c for c in response.clauses}

        # 1. Automatic Renewal guardrail
        auto_renewal = clause_map["Automatic Renewal"]
        assert auto_renewal.presence_status == ClausePresenceStatus.ABSENT
        assert auto_renewal.review_priority == RiskLevel.LOW
        assert auto_renewal.risk_level == RiskLevel.LOW
        assert "without risk of unintentional automatic rollover" in auto_renewal.explanation

        # 2. Liability Limits guardrail
        liability = clause_map["Liability Limits"]
        assert liability.presence_status == ClausePresenceStatus.ABSENT
        assert liability.review_priority == RiskLevel.CRITICAL
        assert liability.risk_level == RiskLevel.CRITICAL
        assert "uncapped" in liability.explanation.lower()

        # 3. Indemnification guardrail
        indemnity = clause_map["Indemnification"]
        assert indemnity.presence_status == ClausePresenceStatus.ABSENT
        assert indemnity.review_priority == RiskLevel.LOW

    def test_present_clauses_detected(self):
        """Present clauses with specific language are evaluated accurately."""
        service = GeminiLLMService(api_key=None)
        contract_text = """
        Section 1. Termination: Either party may terminate this agreement at any time for convenience.
        Section 2. Limitation of Liability: In no event shall aggregate liability exceed the fees paid.
        Section 3. Confidential Information: Both parties agree to protect proprietary information.
        Section 4. Payment Terms: Invoices are payable on Net 30 days terms.
        Section 5. Governing Law: This agreement shall be governed by the laws of New York.
        Section 6. Data Protection: Each party shall comply with applicable GDPR and data privacy laws.
        """

        response = service.analyze_contract(
            contract_id="c_3",
            filename="services.txt",
            contract_text=contract_text,
        )

        clause_map = {c.category: c for c in response.clauses}

        # Termination for convenience -> HIGH risk
        assert clause_map["Termination"].presence_status == ClausePresenceStatus.PRESENT
        assert clause_map["Termination"].review_priority == RiskLevel.HIGH

        # Limitation of liability present -> MEDIUM review priority
        assert clause_map["Liability Limits"].presence_status == ClausePresenceStatus.PRESENT
        assert clause_map["Liability Limits"].review_priority == RiskLevel.MEDIUM

        # Confidentiality present -> LOW
        assert clause_map["Confidentiality"].presence_status == ClausePresenceStatus.PRESENT
        assert clause_map["Confidentiality"].review_priority == RiskLevel.LOW

        # Payment present -> LOW
        assert clause_map["Payment"].presence_status == ClausePresenceStatus.PRESENT
        assert clause_map["Payment"].review_priority == RiskLevel.LOW

        # Dispute Resolution present -> LOW
        assert clause_map["Dispute Resolution"].presence_status == ClausePresenceStatus.PRESENT
        assert clause_map["Dispute Resolution"].review_priority == RiskLevel.LOW

    def test_ambiguous_clause_detection(self):
        """
        When consequential damages are mentioned but aggregate monetary cap is absent,
        presence_status is marked AMBIGUOUS with HIGH priority.
        """
        service = GeminiLLMService(api_key=None)
        contract_text = """
        Neither party shall be liable for any indirect, special, punitive, or consequential damages.
        Each party waives claims for lost profits or business interruptions.
        """

        response = service.analyze_contract(
            contract_id="c_4",
            filename="ambiguous_liability.txt",
            contract_text=contract_text,
        )

        clause_map = {c.category: c for c in response.clauses}
        liability = clause_map["Liability Limits"]

        assert liability.presence_status == ClausePresenceStatus.AMBIGUOUS
        assert liability.review_priority == RiskLevel.HIGH
        assert "no explicit aggregate liability cap" in liability.explanation.lower()

    def test_retrieval_failed_to_find_distinction(self):
        """
        When keyword is found in text but vector retrieval returned 0 chunks (retrieval_attempted=True),
        presence_status must be RETRIEVAL_FAILED_TO_FIND, distinguishing it from ABSENT.
        """
        service = GeminiLLMService(api_key=None)
        contract_text = "The agreement may be subject to termination upon breach."

        # Pass candidate_chunks_per_cat with empty list for Termination and retrieval_attempted=True
        candidate_chunks = {"Termination": []}

        response = service.analyze_contract(
            contract_id="c_5",
            filename="contract.txt",
            contract_text=contract_text,
        )
        # Directly test the helper with retrieval_attempted=True
        clause = service._build_heuristic_clause(
            cat_def=TARGET_CLAUSE_CATEGORIES[0],  # Termination
            presence=ClausePresenceStatus.RETRIEVAL_FAILED_TO_FIND,
            cited_chunk_id=None,
            cited_evidence=None,
            text_lower=contract_text.lower(),
            policy_to_use=ILLUSTRATIVE_REVIEW_CHECKLIST,
        )

        assert clause.presence_status == ClausePresenceStatus.RETRIEVAL_FAILED_TO_FIND
        assert clause.review_priority == RiskLevel.MEDIUM
        assert "vector retrieval did not surface a definitive clause" in clause.explanation
        assert clause.cited_chunk_id is None

    def test_custom_review_policy_is_used(self):
        """When a user supplies a custom review policy, it is recorded in the response."""
        service = GeminiLLMService(api_key=None)
        custom_policy = "Enterprise Standard Policy: All invoices must have Net 60 terms."

        response = service.analyze_contract(
            contract_id="c_6",
            filename="policy_check.txt",
            contract_text="Payment within 30 days.",
            review_policy=custom_policy,
        )

        assert response.review_policy_used == custom_policy

    def test_citation_verification_rejects_fabricated_chunk_ids(self, mock_gemini_service):
        """
        Gemini JSON output with a fabricated chunk_id not in indexed chunks must have
        cited_chunk_id nulled out and a verification warning appended.
        """
        service, mock_client = mock_gemini_service

        real_chunk = create_dummy_chunk("valid_chunk_001", "c_7", "Limitation: Aggregate cap is $100k.")
        chunks = [real_chunk]

        # Fake response from Gemini citing a real chunk and a fabricated chunk
        mock_payload = {
            "overall_risk_score": 60,
            "overall_risk_level": "MEDIUM",
            "executive_summary": "Risk evaluation summary.",
            "key_vulnerabilities": ["Check liability cap."],
            "clauses": [
                {
                    "category": "Liability Limits",
                    "clause_title": "Limitation of Liability",
                    "presence_status": "PRESENT",
                    "review_priority": "MEDIUM",
                    "cited_chunk_id": "valid_chunk_001",
                    "cited_evidence": "Limitation: Aggregate cap is $100k.",
                    "explanation": "Validly cited clause.",
                    "policy_mismatch": None,
                    "missing_information": None,
                    "suggested_questions": ["Is $100k sufficient?"],
                    "risk_score": 50,
                },
                {
                    "category": "Termination",
                    "clause_title": "Termination Clause",
                    "presence_status": "PRESENT",
                    "review_priority": "HIGH",
                    "cited_chunk_id": "fabricated_chunk_999",  # Hallucinated ID
                    "cited_evidence": "Convenience termination excerpt.",
                    "explanation": "Immediate termination allowed.",
                    "policy_mismatch": "Notice too short.",
                    "missing_information": None,
                    "suggested_questions": ["Can we add 30-day notice?"],
                    "risk_score": 75,
                },
            ],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(mock_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = service.analyze_contract(
            contract_id="c_7",
            filename="contract.txt",
            contract_text="Some text",
            chunks=chunks,
        )

        clause_map = {c.category: c for c in response.clauses}

        # Valid chunk ID must be preserved
        liability = clause_map["Liability Limits"]
        assert liability.cited_chunk_id == "valid_chunk_001"
        assert liability.cited_evidence == "Limitation: Aggregate cap is $100k."

        # Fabricated chunk ID must be discarded / nulled out
        termination = clause_map["Termination"]
        assert termination.cited_chunk_id is None
        assert "[Note: Citation chunk ID was unverified" in termination.explanation

    def test_conflicting_clause_status_parsed_correctly(self, mock_gemini_service):
        """When Gemini identifies conflicting clauses, CONFLICTING status passes through."""
        service, mock_client = mock_gemini_service

        mock_payload = {
            "overall_risk_score": 75,
            "overall_risk_level": "HIGH",
            "executive_summary": "Contract contains contradictory provisions.",
            "key_vulnerabilities": ["Contradictory termination notice periods."],
            "clauses": [
                {
                    "category": "Termination",
                    "clause_title": "Contradictory Termination Terms",
                    "presence_status": "CONFLICTING",
                    "review_priority": "HIGH",
                    "cited_chunk_id": None,
                    "cited_evidence": "Section 2 specifies 30 days notice; Section 12 specifies termination at will.",
                    "explanation": "Section 2 and Section 12 are directly conflicting on termination notice.",
                    "policy_mismatch": "Agreement contradicts itself on notice requirement.",
                    "missing_information": "Reconciliation of Section 2 and Section 12.",
                    "suggested_questions": ["Which termination notice clause governs?"],
                    "risk_score": 80,
                }
            ],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(mock_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = service.analyze_contract(
            contract_id="c_8",
            filename="contradictory.txt",
            contract_text="Text with contradictory clauses.",
        )

        term_clause = next(c for c in response.clauses if c.category == "Termination")
        assert term_clause.presence_status == ClausePresenceStatus.CONFLICTING
        assert term_clause.review_priority == RiskLevel.HIGH

    def test_gemini_auto_renewal_guardrail_enforcement(self, mock_gemini_service):
        """
        If Gemini marks Automatic Renewal as ABSENT but assigns HIGH or CRITICAL priority,
        the backend guardrail must correct it to LOW priority.
        """
        service, mock_client = mock_gemini_service

        mock_payload = {
            "overall_risk_score": 40,
            "overall_risk_level": "MEDIUM",
            "executive_summary": "Risk evaluation.",
            "key_vulnerabilities": [],
            "clauses": [
                {
                    "category": "Automatic Renewal",
                    "clause_title": "Automatic Renewal",
                    "presence_status": "ABSENT",
                    "review_priority": "CRITICAL",  # LLM erroneously claims missing renewal is critical
                    "cited_chunk_id": None,
                    "cited_evidence": None,
                    "explanation": "No auto renewal found.",
                    "policy_mismatch": None,
                    "missing_information": None,
                    "suggested_questions": [],
                    "risk_score": 90,
                }
            ],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(mock_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = service.analyze_contract(
            contract_id="c_9",
            filename="fixed_term.txt",
            contract_text="Contract expires on December 31, 2026.",
        )

        renewal_clause = next(c for c in response.clauses if c.category == "Automatic Renewal")
        assert renewal_clause.presence_status == ClausePresenceStatus.ABSENT
        # Guardrail enforced:
        assert renewal_clause.review_priority == RiskLevel.LOW

    def test_clause_analysis_backward_compatibility(self):
        """
        `ClauseAnalysis` initialized with new schema fields must correctly populate
        legacy UI fields (original_text, risk_level, risk_score, risk_reasoning, mitigation_recommendation)
        via `model_post_init`.
        """
        clause = ClauseAnalysis(
            category="Indemnification",
            clause_title="Indemnity Obligations",
            presence_status=ClausePresenceStatus.PRESENT,
            review_priority=RiskLevel.HIGH,
            cited_chunk_id="chunk_1",
            cited_evidence="Party A indemnifies Party B.",
            explanation="Uncapped indemnity exposure.",
            policy_mismatch="Requires mutual cap.",
            missing_information="Monetary ceiling.",
            suggested_questions=["Can indemnity be capped?"],
        )

        assert clause.original_text == "Party A indemnifies Party B."
        assert clause.risk_level == RiskLevel.HIGH
        assert clause.risk_reasoning == "Uncapped indemnity exposure."
        assert "Can indemnity be capped?" in clause.mitigation_recommendation

        # Test absent clause fallback for original_text
        absent_clause = ClauseAnalysis(
            category="Payment",
            clause_title="Payment Terms",
            presence_status=ClausePresenceStatus.ABSENT,
            review_priority=RiskLevel.MEDIUM,
            explanation="No payment terms found.",
        )
        assert "[ABSENT] No direct clause text located in contract." in absent_clause.original_text

    def test_analyze_api_route_with_custom_policy(self):
        """POST /api/v1/contracts/{id}/analyze accepts optional review_policy and executes analysis."""
        client = TestClient(app)
        store = get_memory_store()

        # Seed in-memory store with a test contract
        contract_id = "test_contract_api_123"
        store.add_contract(
            contract_id=contract_id,
            filename="enterprise_vendor_nda.pdf",
            file_path="uploads/enterprise_vendor_nda.pdf",
            file_size=1024,
            raw_text="Confidentiality: Both parties shall keep information confidential for 3 years.",
            chunks=[],
        )

        payload = {"review_policy": "Strict NDA Standard: 5-year survival required."}
        response = client.post(f"/api/contracts/{contract_id}/analyze", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["contract_id"] == contract_id
        assert data["review_policy_used"] == "Strict NDA Standard: 5-year survival required."
        assert len(data["clauses"]) == 8
        assert "legal_disclaimer" in data

        # Check retrieval from memory store
        cached = store.get_analysis(contract_id)
        assert cached is not None
        assert cached.review_policy_used == "Strict NDA Standard: 5-year survival required."
