import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_memory_store
from app.models.schemas import (
    CitationSource,
    ClausePresenceStatus,
    ContractComparisonResponse,
    DocumentChunk,
    RiskLevel,
)
from app.services.llm_service import GeminiLLMService, TARGET_CLAUSE_CATEGORIES

CONTRACT_A_TEXT = """MASTER SAAS AGREEMENT (VENDOR FORM)
ARTICLE 1. TERMINATION
Vendor may terminate this agreement at any time for convenience upon thirty (30) days prior written notice.
Customer may terminate solely in the event of an uncured material breach by Vendor with thirty (30) days cure notice.

ARTICLE 2. PAYMENT TERMS
All invoices are payable Net 15 days from invoice date.
Late payments shall incur 1.5% monthly late interest fee on overdue charges.

ARTICLE 3. LIMITATION OF LIABILITY
Vendor's aggregate liability under this agreement shall in no event exceed the fees paid in the preceding three (3) months ($10,000 cap).
Neither party shall be liable for indirect, incidental, or consequential damages.

ARTICLE 4. INDEMNIFICATION
Customer agrees to defend and indemnify Vendor against all third-party claims arising from Customer data or IP infringement.
Vendor provides no indemnification to Customer under any circumstances.

ARTICLE 5. AUTOMATIC RENEWAL
This Agreement shall automatically renew for successive one (1) year terms unless either party provides written notice of non-renewal at least ninety (90) days prior to expiration.

ARTICLE 6. CONFIDENTIALITY
Mutual confidentiality obligations shall survive for a period of two (2) years following termination.

ARTICLE 7. DATA PROTECTION
Vendor will implement reasonable security standards.
In the event of a security breach, Vendor will notify Customer within thirty (30) days.

ARTICLE 8. DISPUTE RESOLUTION & GOVERNING LAW
This agreement is governed by the laws of Delaware.
All disputes shall be resolved through binding commercial arbitration in Wilmington, Delaware.
"""

CONTRACT_B_TEXT = """ENTERPRISE SERVICES AGREEMENT (BUYER FORM)
SECTION 1. TERMINATION
Either party may terminate this agreement for convenience upon sixty (60) days prior written notice.
Either party may terminate for material breach with fifteen (15) days cure notice.

SECTION 2. PAYMENT TERMS
Invoices are payable on Net 60 days terms.
No interest or late fees shall accrue on disputed or overdue amounts.

SECTION 3. LIMITATION OF LIABILITY
Each party's aggregate liability shall be capped at twelve (12) months fees or $500,000, whichever is greater.
The aggregate liability cap shall not apply to breaches of confidentiality, data protection obligations, or indemnification claims.

SECTION 4. INDEMNIFICATION
Mutual indemnification. Each party agrees to defend, indemnify, and hold harmless the other party from all third-party intellectual property infringement claims and gross negligence.

SECTION 5. TERM AND EXPIRATION
This agreement commences on the Effective Date and concludes after twelve (12) months of performance, after which this agreement shall permanently expire.

SECTION 6. CONFIDENTIALITY
Proprietary information obligations shall survive for five (5) years following termination, and trade secrets shall be protected perpetually.

SECTION 7. DATA PROTECTION
Vendor shall strictly comply with GDPR and CCPA.
Vendor must notify Customer of any data security breach within forty-eight (48) hours of discovery.

SECTION 8. DISPUTE RESOLUTION & GOVERNING LAW
This agreement shall be governed by the laws of California.
Any legal action shall be brought exclusively in the state or federal courts in San Francisco, California.
"""


def create_dummy_chunk(chunk_id: str, doc_id: str, text: str, section: str = "General") -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        contract_id=doc_id,
        filename=f"{doc_id}.pdf",
        chunk_index=0,
        text=text,
        start_char=0,
        end_char=len(text),
        page_number=1,
        section=section,
        section_title=section,
        char_count=len(text),
        word_count=len(text.split()),
    )


class TestContractComparison:
    """Unit tests for ContractLens side-by-side contract comparison."""

    @pytest.fixture
    def mock_gemini_service(self):
        with patch("app.services.llm_service.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            service = GeminiLLMService(api_key="mock_key")
            service._client = mock_client
            yield service, mock_client

    def test_compare_two_synthetic_contracts_heuristic_all_categories(self):
        """Heuristic comparison must evaluate all 8 core categories and include legal disclaimer."""
        service = GeminiLLMService(api_key=None)

        response = service.compare_contracts(
            contract_a_id="saas_vendor_1",
            contract_a_filename="Vendor_SaaS.pdf",
            contract_a_text=CONTRACT_A_TEXT,
            contract_b_id="enterprise_buyer_2",
            contract_b_filename="Buyer_Enterprise.pdf",
            contract_b_text=CONTRACT_B_TEXT,
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

        assert "Vendor_SaaS.pdf" in response.executive_summary
        assert "Buyer_Enterprise.pdf" in response.executive_summary
        assert "Does not constitute legal advice and does not declare either agreement legally superior." in response.legal_disclaimer
        assert len(response.key_differences) > 0

    def test_known_differences_accurately_extracted(self):
        """Verify known differences between Vendor-form Contract A and Buyer-form Contract B."""
        service = GeminiLLMService(api_key=None)

        response = service.compare_contracts(
            contract_a_id="saas_vendor_1",
            contract_a_filename="Vendor_SaaS.pdf",
            contract_a_text=CONTRACT_A_TEXT,
            contract_b_id="enterprise_buyer_2",
            contract_b_filename="Buyer_Enterprise.pdf",
            contract_b_text=CONTRACT_B_TEXT,
        )

        clause_map = {c.category: c for c in response.clauses}

        # 1. Termination: Convenience differences
        termination = clause_map["Termination"]
        assert termination.contract_a.presence_status == ClausePresenceStatus.PRESENT
        assert termination.contract_b.presence_status == ClausePresenceStatus.PRESENT
        assert "notice" in termination.difference_summary.lower()
        assert termination.review_significance in (RiskLevel.MEDIUM, RiskLevel.HIGH)

        # 2. Payment: Net 15 + interest vs Net 60
        payment = clause_map["Payment"]
        assert "net 15" in payment.contract_a.summary.lower()
        assert "net 60" in payment.contract_b.summary.lower()
        assert "payment" in payment.difference_summary.lower()

        # 3. Liability Limits: $10,000 cap vs $500,000 with carve-outs
        liability = clause_map["Liability Limits"]
        assert "$10,000" in liability.contract_a.summary
        assert "$500,000" in liability.contract_b.summary
        assert "carve-outs" in liability.contract_b.summary

        # 4. Indemnification: Unilateral vs Mutual
        indemnity = clause_map["Indemnification"]
        assert indemnity.contract_a.presence_status == ClausePresenceStatus.PRESENT
        assert indemnity.contract_b.presence_status == ClausePresenceStatus.PRESENT
        assert "indemnif" in indemnity.difference_summary.lower()

        # 5. Automatic Renewal: Contract A present vs Contract B ABSENT
        renewal = clause_map["Automatic Renewal"]
        assert renewal.contract_a.presence_status == ClausePresenceStatus.PRESENT
        assert renewal.contract_b.presence_status == ClausePresenceStatus.ABSENT
        assert "omits" in renewal.difference_summary.lower() or "absent" in renewal.difference_summary.lower()

        # 6. Confidentiality: 2 years vs 5 years
        confidentiality = clause_map["Confidentiality"]
        assert "2-year" in confidentiality.contract_a.summary
        assert "5-year" in confidentiality.contract_b.summary

        # 7. Data Protection: 30 days vs 48 hours
        data_prot = clause_map["Data Protection"]
        assert "30 days" in data_prot.contract_a.summary
        assert "48 hours" in data_prot.contract_b.summary

        # 8. Dispute Resolution: Delaware/Arbitration vs California/Courts
        dispute = clause_map["Dispute Resolution"]
        assert "delaware" in dispute.contract_a.summary.lower()
        assert "california" in dispute.contract_b.summary.lower()

    def test_distinguish_absent_from_retrieval_failed(self):
        """
        Distinct presence statuses must be properly differentiated:
        - ABSENT: topic not mentioned at all.
        - RETRIEVAL_FAILED_TO_FIND: keywords mentioned in text, but retrieval returned 0 chunks.
        """
        service = GeminiLLMService(api_key=None)

        clause = service._build_heuristic_comparison_clause(
            cat_def=TARGET_CLAUSE_CATEGORIES[0],  # Termination
            contract_a_id="doc_a",
            contract_a_filename="ContractA.pdf",
            presence_a=ClausePresenceStatus.RETRIEVAL_FAILED_TO_FIND,
            cited_chunk_id_a=None,
            cited_evidence_a=None,
            citation_a=None,
            text_a_lower="contract mentions termination keywords",
            contract_b_id="doc_b",
            contract_b_filename="ContractB.pdf",
            presence_b=ClausePresenceStatus.ABSENT,
            cited_chunk_id_b=None,
            cited_evidence_b=None,
            citation_b=None,
            text_b_lower="no termination words",
        )

        assert clause.contract_a.presence_status == ClausePresenceStatus.RETRIEVAL_FAILED_TO_FIND
        assert clause.contract_b.presence_status == ClausePresenceStatus.ABSENT
        assert "vector retrieval did not isolate a definitive clause" in clause.difference_summary
        assert clause.contract_a.cited_chunk_id is None
        assert clause.contract_b.cited_chunk_id is None

    def test_gemini_comparison_structured_json_and_citation_verification(self, mock_gemini_service):
        """
        Gemini JSON output:
        - Valid chunk IDs for Contract A and B are preserved and verified.
        - Fabricated chunk IDs for Contract A are nulled out and appended with verification note.
        """
        service, mock_client = mock_gemini_service

        chunk_a = create_dummy_chunk("valid_a_001", "saas_vendor_1", "Vendor termination for convenience.")
        chunk_b = create_dummy_chunk("valid_b_001", "enterprise_buyer_2", "Buyer 60 days convenience termination.")

        mock_payload = {
            "executive_summary": "Comparison shows key trade-offs in termination flexibility and liability caps.",
            "key_differences": [
                "Termination: 30 days vs 60 days notice.",
                "Liability: $10,000 cap vs $500,000 cap.",
            ],
            "clauses": [
                {
                    "category": "Termination",
                    "clause_title": "Termination Comparison",
                    "contract_a_presence": "PRESENT",
                    "contract_a_chunk_id": "valid_a_001",  # Real ID
                    "contract_a_evidence": "Vendor termination for convenience.",
                    "contract_a_summary": "Vendor convenience termination.",
                    "contract_b_presence": "PRESENT",
                    "contract_b_chunk_id": "valid_b_001",  # Real ID
                    "contract_b_evidence": "Buyer 60 days convenience termination.",
                    "contract_b_summary": "Mutual 60 days convenience termination.",
                    "difference_summary": "Contract A offers shorter notice; Contract B requires 60 days.",
                    "human_review_rationale": "Assess operational runway required upon contract cancellation.",
                    "suggested_questions": ["Is 30 days notice adequate?"],
                    "review_significance": "HIGH",
                },
                {
                    "category": "Payment",
                    "clause_title": "Payment Terms Comparison",
                    "contract_a_presence": "PRESENT",
                    "contract_a_chunk_id": "fabricated_chunk_a_999",  # Hallucinated ID
                    "contract_a_evidence": "Net 15 days.",
                    "contract_a_summary": "Net 15 days.",
                    "contract_b_presence": "PRESENT",
                    "contract_b_chunk_id": "valid_b_001",
                    "contract_b_evidence": "Net 60 days.",
                    "contract_b_summary": "Net 60 days.",
                    "difference_summary": "Net 15 vs Net 60.",
                    "human_review_rationale": "Cash flow and working capital impact.",
                    "suggested_questions": ["Can terms be aligned to Net 30?"],
                    "review_significance": "MEDIUM",
                },
            ],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(mock_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = service.compare_contracts(
            contract_a_id="saas_vendor_1",
            contract_a_filename="Vendor_SaaS.pdf",
            contract_a_text=CONTRACT_A_TEXT,
            contract_a_chunks=[chunk_a],
            contract_b_id="enterprise_buyer_2",
            contract_b_filename="Buyer_Enterprise.pdf",
            contract_b_text=CONTRACT_B_TEXT,
            contract_b_chunks=[chunk_b],
        )

        clause_map = {c.category: c for c in response.clauses}

        # Termination: Both chunk IDs verified and preserved
        term = clause_map["Termination"]
        assert term.contract_a.cited_chunk_id == "valid_a_001"
        assert term.contract_a.citation is not None
        assert term.contract_b.cited_chunk_id == "valid_b_001"
        assert term.contract_b.citation is not None

        # Payment: Fabricated chunk ID for Contract A must be nulled out
        payment = clause_map["Payment"]
        assert payment.contract_a.cited_chunk_id is None
        assert "[Note: Contract A citation chunk ID was unverified" in payment.human_review_rationale
        assert payment.contract_b.cited_chunk_id == "valid_b_001"

    def test_neutrality_guardrail_present(self):
        """Comparison responses must remain legally neutral and never declare superiority."""
        service = GeminiLLMService(api_key=None)

        response = service.compare_contracts(
            contract_a_id="saas_vendor_1",
            contract_a_filename="Vendor_SaaS.pdf",
            contract_a_text=CONTRACT_A_TEXT,
            contract_b_id="enterprise_buyer_2",
            contract_b_filename="Buyer_Enterprise.pdf",
            contract_b_text=CONTRACT_B_TEXT,
        )

        # Check disclaimer
        assert "Does not constitute legal advice and does not declare either agreement legally superior." in response.legal_disclaimer

        # Check that executive summary and difference summaries avoid claiming legal superiority
        forbidden_phrases = ["legally superior", "is the winner", "better contract", "strictly superior"]
        for phrase in forbidden_phrases:
            assert phrase not in response.executive_summary.lower()
            for c in response.clauses:
                assert phrase not in c.difference_summary.lower()

    def test_compare_api_endpoint_post(self):
        """POST /api/contracts/compare executes comparison between two in-memory contracts."""
        client = TestClient(app)
        store = get_memory_store()

        id_a = "contract_compare_a"
        id_b = "contract_compare_b"

        store.add_contract(
            contract_id=id_a,
            filename="Vendor_Form.pdf",
            file_path="uploads/Vendor_Form.pdf",
            file_size=2048,
            raw_text=CONTRACT_A_TEXT,
            chunks=[],
        )
        store.add_contract(
            contract_id=id_b,
            filename="Buyer_Form.pdf",
            file_path="uploads/Buyer_Form.pdf",
            file_size=2048,
            raw_text=CONTRACT_B_TEXT,
            chunks=[],
        )

        payload = {
            "contract_a_id": id_a,
            "contract_b_id": id_b,
            "focus_categories": ["Termination", "Payment", "Liability Limits"],
        }
        res = client.post("/api/contracts/compare", json=payload)

        assert res.status_code == 200
        data = res.json()
        assert data["contract_a_id"] == id_a
        assert data["contract_b_id"] == id_b
        assert len(data["clauses"]) >= 3
        assert "legal_disclaimer" in data

        # Check store cached comparison
        cache_key = f"{id_a}:{id_b}"
        cached = store.get_comparison(cache_key)
        assert cached is not None
        assert cached.contract_a_id == id_a

    def test_compare_api_endpoint_get(self):
        """GET /api/contracts/compare/{id_a}/{id_b} returns comparison."""
        client = TestClient(app)
        id_a = "contract_compare_a"
        id_b = "contract_compare_b"

        res = client.get(f"/api/contracts/compare/{id_a}/{id_b}")
        assert res.status_code == 200
        data = res.json()
        assert data["contract_a_id"] == id_a
        assert data["contract_b_id"] == id_b

    def test_compare_api_endpoint_validation_errors(self):
        """POST /api/contracts/compare returns 400 when comparing contract with itself, 404 for non-existent."""
        client = TestClient(app)

        # 400 for same contract
        same_payload = {"contract_a_id": "c1", "contract_b_id": "c1"}
        res = client.post("/api/contracts/compare", json=same_payload)
        assert res.status_code == 400
        assert "Cannot compare a contract with itself" in res.json()["detail"]

        # 404 for missing contract
        missing_payload = {"contract_a_id": "non_existent_123", "contract_b_id": "also_missing_456"}
        res = client.post("/api/contracts/compare", json=missing_payload)
        assert res.status_code == 404
