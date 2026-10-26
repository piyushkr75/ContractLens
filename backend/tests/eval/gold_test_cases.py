"""
ContractLens Evaluation Suite — Gold-Standard Test Cases
==========================================================

40 manually verified question–answer pairs covering:
- Termination (6 cases)
- Indemnity (5 cases)
- Liability (5 cases)
- Renewal (4 cases)
- Payments (5 cases)
- Missing clauses (5 cases)
- Conflicting clauses (5 cases)
- Unsupported / out-of-scope questions (5 cases)

Each test case specifies:
- question: natural-language user query
- contract_id: which synthetic contract the question targets
- category: clause category being tested
- expected_evidence_status: SUFFICIENT, PARTIAL, INSUFFICIENT, or CONFLICTING
- expected_answer_keywords: substrings that MUST appear in a correct answer
- expected_absent_keywords: substrings that must NOT appear (for abstention)
- expected_risk_level: if a risk-analysis test, the expected RiskLevel
- is_abstention_case: True if the system should decline to answer
- is_conflict_case: True if conflicting clauses should be flagged
- ground_truth_answer: canonical short-form answer for human comparison
- relevant_sections: section references the retrieval should surface
- notes: evaluator notes
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EvalTestCase:
    """A single evaluation test case with ground-truth annotations."""
    test_id: str
    question: str
    contract_id: str
    category: str
    expected_evidence_status: str  # SUFFICIENT | PARTIAL | INSUFFICIENT | CONFLICTING
    expected_answer_keywords: List[str] = field(default_factory=list)
    expected_absent_keywords: List[str] = field(default_factory=list)
    expected_risk_level: Optional[str] = None  # LOW | MEDIUM | HIGH | CRITICAL
    is_abstention_case: bool = False
    is_conflict_case: bool = False
    ground_truth_answer: str = ""
    relevant_sections: List[str] = field(default_factory=list)
    notes: str = ""


# ==========================================================================
# TERMINATION (6 cases)
# ==========================================================================

TERMINATION_CASES = [
    EvalTestCase(
        test_id="TERM-001",
        question="What is the notice period required for termination for convenience?",
        contract_id="eval_acme_beta_001",
        category="Termination",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["ninety", "90", "days", "written notice"],
        ground_truth_answer="Either party may terminate for convenience upon 90 days prior written notice (Section 8.1).",
        relevant_sections=["Section 8"],
    ),
    EvalTestCase(
        test_id="TERM-002",
        question="How long does the breaching party have to cure a material breach before termination?",
        contract_id="eval_acme_beta_001",
        category="Termination",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["thirty", "30", "days", "cure"],
        ground_truth_answer="The breaching party has 30 days to cure a material breach after receiving written notice (Section 8.2).",
        relevant_sections=["Section 8"],
    ),
    EvalTestCase(
        test_id="TERM-003",
        question="Can the licensee terminate early for cause?",
        contract_id="eval_omega_sigma_002",
        category="Termination",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["end of", "term", "sixty", "60"],
        expected_absent_keywords=["cure period"],
        ground_truth_answer="Licensee may only terminate at the end of the current term with 60 days notice. There is no cure period and no mid-term termination right for Licensee.",
        relevant_sections=["Section 6"],
        expected_risk_level="HIGH",
        notes="One-sided — Licensor can terminate immediately, Licensee cannot.",
    ),
    EvalTestCase(
        test_id="TERM-004",
        question="Is there a cure period for the employee bond termination?",
        contract_id="eval_delta_epsilon_003",
        category="Termination",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["ninety", "90", "notice"],
        ground_truth_answer="There is a 90-day notice period (Clause 4.1) but no cure period for breach.",
        relevant_sections=["Clause 4"],
    ),
    EvalTestCase(
        test_id="TERM-005",
        question="What is the termination notice period in this supply agreement?",
        contract_id="eval_greenleaf_terra_004",
        category="Termination",
        expected_evidence_status="CONFLICTING",
        expected_answer_keywords=["thirty", "30", "one hundred and eighty", "180"],
        is_conflict_case=True,
        ground_truth_answer="Conflicting: Section 7.1 says 30 days, but Section 12.1 (amendment) extends it to 180 days.",
        relevant_sections=["Section 7", "Section 12"],
        notes="Key conflicting-clause test case.",
    ),
    EvalTestCase(
        test_id="TERM-006",
        question="What happens after termination of the DPA?",
        contract_id="eval_novahealth_medicore_005",
        category="Termination",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["return", "delete", "forty-five", "45", "days"],
        ground_truth_answer="Processor must return or securely delete all Personal Data within 45 days using NIST SP 800-88 methods (Article 10.3).",
        relevant_sections=["Article 10"],
    ),
]

# ==========================================================================
# INDEMNIFICATION (5 cases)
# ==========================================================================

INDEMNITY_CASES = [
    EvalTestCase(
        test_id="INDEM-001",
        question="Is indemnification mutual or one-sided in the ACME-BetaCorp agreement?",
        contract_id="eval_acme_beta_001",
        category="Indemnification",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["mutual", "provider", "client"],
        ground_truth_answer="Mutual. Provider indemnifies Client for negligence/IP infringement; Client indemnifies Provider for misuse of deliverables (Section 10).",
        relevant_sections=["Section 10"],
    ),
    EvalTestCase(
        test_id="INDEM-002",
        question="Does the Omega Software Licence include a mutual indemnification clause?",
        contract_id="eval_omega_sigma_002",
        category="Indemnification",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["one-sided", "licensee", "no licensor"],
        expected_absent_keywords=["mutual"],
        ground_truth_answer="No. Only Licensee indemnifies Licensor (Section 7.1). Licensor has no indemnification obligation (Section 7.2).",
        relevant_sections=["Section 7"],
        expected_risk_level="HIGH",
        notes="Should flag as HIGH risk — completely one-sided.",
    ),
    EvalTestCase(
        test_id="INDEM-003",
        question="Is there an indemnification cap in the ACME-BetaCorp MSA?",
        contract_id="eval_acme_beta_001",
        category="Indemnification",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["twelve", "12", "months", "fees"],
        ground_truth_answer="Yes. Each party's aggregate indemnification is capped at fees paid in the preceding 12 months (Section 10.3).",
        relevant_sections=["Section 10"],
    ),
    EvalTestCase(
        test_id="INDEM-004",
        question="Are data breach indemnification obligations capped in the DPA?",
        contract_id="eval_novahealth_medicore_005",
        category="Indemnification",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["uncapped", "wilful", "gross"],
        ground_truth_answer="No — wilful or grossly negligent data breaches are explicitly uncapped (Article 8.2), overriding the general cap in Article 9.",
        relevant_sections=["Article 8", "Article 9"],
    ),
    EvalTestCase(
        test_id="INDEM-005",
        question="Does the employment bond include indemnification provisions?",
        contract_id="eval_delta_epsilon_003",
        category="Indemnification",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_answer_keywords=["no", "absent", "not", "indemnif"],
        ground_truth_answer="No indemnification provisions exist in the employment bond agreement.",
        relevant_sections=[],
        notes="This clause is intentionally absent.",
    ),
]

# ==========================================================================
# LIABILITY LIMITS (5 cases)
# ==========================================================================

LIABILITY_CASES = [
    EvalTestCase(
        test_id="LIAB-001",
        question="What is the aggregate liability cap in the ACME-BetaCorp MSA?",
        contract_id="eval_acme_beta_001",
        category="Liability Limits",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["twelve", "12", "months", "fees"],
        ground_truth_answer="Total aggregate liability is capped at fees paid in the preceding 12 months (Section 11.1), with carve-outs for Sections 10 and 12.",
        relevant_sections=["Section 11"],
    ),
    EvalTestCase(
        test_id="LIAB-002",
        question="Are consequential damages excluded in the MSA?",
        contract_id="eval_acme_beta_001",
        category="Liability Limits",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["consequential", "indirect", "excluded", "waiv"],
        ground_truth_answer="Yes. Section 11.2 mutually excludes indirect, incidental, special, consequential, and punitive damages.",
        relevant_sections=["Section 11"],
    ),
    EvalTestCase(
        test_id="LIAB-003",
        question="Does the Omega licence agreement contain a limitation of liability?",
        contract_id="eval_omega_sigma_002",
        category="Liability Limits",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_answer_keywords=["no", "absent", "missing", "limitation of liability"],
        ground_truth_answer="No. The Omega licence contains no limitation of liability clause, creating uncapped exposure.",
        relevant_sections=[],
        notes="Intentionally missing — should be flagged as CRITICAL risk.",
        expected_risk_level="CRITICAL",
    ),
    EvalTestCase(
        test_id="LIAB-004",
        question="What is the liability cap in the DPA?",
        contract_id="eval_novahealth_medicore_005",
        category="Liability Limits",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["1,500,000", "€1,500,000", "twenty-four", "24", "months"],
        ground_truth_answer="€1,500,000 or total fees paid in the preceding 24 months, whichever is greater (Article 9.1).",
        relevant_sections=["Article 9"],
    ),
    EvalTestCase(
        test_id="LIAB-005",
        question="What is the supply agreement's liability cap duration basis?",
        contract_id="eval_greenleaf_terra_004",
        category="Liability Limits",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["six", "6", "months"],
        ground_truth_answer="Total fees paid during the preceding 6 months (Section 10.1).",
        relevant_sections=["Section 10"],
    ),
]

# ==========================================================================
# RENEWAL (4 cases)
# ==========================================================================

RENEWAL_CASES = [
    EvalTestCase(
        test_id="RENEW-001",
        question="Does the ACME-BetaCorp MSA auto-renew?",
        contract_id="eval_acme_beta_001",
        category="Automatic Renewal",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["automatically", "renew", "twelve", "12", "sixty", "60"],
        ground_truth_answer="Yes. Auto-renews for 12-month periods unless 60 days notice of non-renewal is given (Section 3.2).",
        relevant_sections=["Section 3"],
    ),
    EvalTestCase(
        test_id="RENEW-002",
        question="Does the Omega licence auto-renew?",
        contract_id="eval_omega_sigma_002",
        category="Automatic Renewal",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["no", "expires", "without", "automatic"],
        ground_truth_answer="No. The agreement expires at the end of the 12-month term without automatic renewal (Section 2).",
        relevant_sections=["Section 2"],
    ),
    EvalTestCase(
        test_id="RENEW-003",
        question="Is there an automatic renewal clause in the employment bond?",
        contract_id="eval_delta_epsilon_003",
        category="Automatic Renewal",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_answer_keywords=["no", "absent", "not"],
        ground_truth_answer="No automatic renewal clause exists in the employment bond.",
        relevant_sections=[],
    ),
    EvalTestCase(
        test_id="RENEW-004",
        question="Does the DPA auto-renew or expire with the underlying services agreement?",
        contract_id="eval_novahealth_medicore_005",
        category="Automatic Renewal",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["duration", "underlying", "services"],
        ground_truth_answer="The DPA remains in effect for the duration of the underlying EHR services agreement (Article 10.1).",
        relevant_sections=["Article 10"],
    ),
]

# ==========================================================================
# PAYMENT TERMS (5 cases)
# ==========================================================================

PAYMENT_CASES = [
    EvalTestCase(
        test_id="PAY-001",
        question="What are the payment terms in the ACME-BetaCorp MSA?",
        contract_id="eval_acme_beta_001",
        category="Payment",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["thirty", "30", "Net 30"],
        ground_truth_answer="Net 30 — invoices are due within 30 days. Late payments accrue 1.5% monthly interest (Section 5).",
        relevant_sections=["Section 5"],
    ),
    EvalTestCase(
        test_id="PAY-002",
        question="What is the bond penalty amount in the employment agreement?",
        contract_id="eval_delta_epsilon_003",
        category="Payment",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["2,00,000", "two lakhs", "₹2,00,000", "200000", "Two Lakhs"],
        ground_truth_answer="₹2,00,000 (Rupees Two Lakhs) as liquidated damages, reduced pro-rata for completed months (Clause 3.2-3.3).",
        relevant_sections=["Clause 3"],
    ),
    EvalTestCase(
        test_id="PAY-003",
        question="What are the payment terms for the supply agreement?",
        contract_id="eval_greenleaf_terra_004",
        category="Payment",
        expected_evidence_status="CONFLICTING",
        expected_answer_keywords=["forty-five", "45", "ninety", "90"],
        is_conflict_case=True,
        ground_truth_answer="Conflicting: Section 4 specifies Net 45, but Section 11.1 (amendment) specifies Net 90 for orders exceeding £50,000.",
        relevant_sections=["Section 4", "Section 11"],
    ),
    EvalTestCase(
        test_id="PAY-004",
        question="Are the Omega licence fees refundable?",
        contract_id="eval_omega_sigma_002",
        category="Payment",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["non-refundable", "no", "refund"],
        ground_truth_answer="No. All fees paid are non-refundable under any circumstances (Section 3.3).",
        relevant_sections=["Section 3"],
    ),
    EvalTestCase(
        test_id="PAY-005",
        question="How much is the monthly processing fee in the DPA?",
        contract_id="eval_novahealth_medicore_005",
        category="Payment",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["€25,000", "25,000"],
        ground_truth_answer="€25,000 per month for hosting up to 500,000 patient records (Article 3.1).",
        relevant_sections=["Article 3"],
    ),
]

# ==========================================================================
# MISSING CLAUSES (5 cases)
# ==========================================================================

MISSING_CLAUSE_CASES = [
    EvalTestCase(
        test_id="MISS-001",
        question="What are the limitation of liability terms in the Omega licence?",
        contract_id="eval_omega_sigma_002",
        category="Liability Limits",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_risk_level="CRITICAL",
        expected_answer_keywords=["no", "absent", "missing", "not"],
        ground_truth_answer="No limitation of liability clause exists in the Omega licence agreement.",
        relevant_sections=[],
    ),
    EvalTestCase(
        test_id="MISS-002",
        question="What data protection provisions does the Omega licence include?",
        contract_id="eval_omega_sigma_002",
        category="Data Protection",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_risk_level="HIGH",
        expected_answer_keywords=["no", "absent", "missing", "not", "data protection"],
        ground_truth_answer="No data protection, GDPR, or CCPA provisions exist in the Omega licence.",
        relevant_sections=[],
    ),
    EvalTestCase(
        test_id="MISS-003",
        question="Is there an indemnification clause in the employment bond?",
        contract_id="eval_delta_epsilon_003",
        category="Indemnification",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_risk_level="LOW",
        expected_answer_keywords=["no", "absent", "not", "indemnif"],
        ground_truth_answer="The employment bond does not include any indemnification provisions.",
        relevant_sections=[],
    ),
    EvalTestCase(
        test_id="MISS-004",
        question="Does the supply agreement include data protection terms?",
        contract_id="eval_greenleaf_terra_004",
        category="Data Protection",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_risk_level="MEDIUM",
        expected_answer_keywords=["no", "absent", "missing", "not", "data protection"],
        ground_truth_answer="The supply agreement does not include data protection or privacy provisions.",
        relevant_sections=[],
    ),
    EvalTestCase(
        test_id="MISS-005",
        question="Does the employment bond have an automatic renewal clause?",
        contract_id="eval_delta_epsilon_003",
        category="Automatic Renewal",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_risk_level="LOW",
        expected_answer_keywords=["no", "absent", "not", "renewal"],
        ground_truth_answer="No automatic renewal clause exists. The bond covers a fixed lock-in period.",
        relevant_sections=[],
    ),
]

# ==========================================================================
# CONFLICTING CLAUSES (5 cases)
# ==========================================================================

CONFLICT_CASES = [
    EvalTestCase(
        test_id="CONF-001",
        question="What is the termination notice period in the supply agreement?",
        contract_id="eval_greenleaf_terra_004",
        category="Termination",
        expected_evidence_status="CONFLICTING",
        expected_answer_keywords=["thirty", "30", "one hundred and eighty", "180", "conflict"],
        is_conflict_case=True,
        expected_risk_level="HIGH",
        ground_truth_answer="Conflicting provisions: Section 7.1 requires 30 days notice; Section 12.1 (amendment) requires 180 days.",
        relevant_sections=["Section 7", "Section 12"],
    ),
    EvalTestCase(
        test_id="CONF-002",
        question="How many days does the buyer have to pay invoices in the supply agreement?",
        contract_id="eval_greenleaf_terra_004",
        category="Payment",
        expected_evidence_status="CONFLICTING",
        expected_answer_keywords=["forty-five", "45", "ninety", "90"],
        is_conflict_case=True,
        expected_risk_level="MEDIUM",
        ground_truth_answer="Conflicting: Net 45 standard (Section 4.1) vs. Net 90 for orders over £50,000 (Section 11.1 amendment).",
        relevant_sections=["Section 4", "Section 11"],
    ),
    EvalTestCase(
        test_id="CONF-003",
        question="Are there any conflicting provisions in the GreenLeaf–TerraCo agreement?",
        contract_id="eval_greenleaf_terra_004",
        category="Termination",
        expected_evidence_status="CONFLICTING",
        expected_answer_keywords=["conflict", "amendment", "notwithstanding"],
        is_conflict_case=True,
        expected_risk_level="HIGH",
        ground_truth_answer="Yes. Sections 11 and 12 (amendments) create conflicts with Sections 4 and 7 on payment and termination terms.",
        relevant_sections=["Section 4", "Section 7", "Section 11", "Section 12"],
    ),
    EvalTestCase(
        test_id="CONF-004",
        question="Can the Buyer terminate the supply agreement with just 30 days notice?",
        contract_id="eval_greenleaf_terra_004",
        category="Termination",
        expected_evidence_status="CONFLICTING",
        expected_answer_keywords=["30", "180", "conflict", "amendment"],
        is_conflict_case=True,
        expected_risk_level="HIGH",
        ground_truth_answer="Unclear. Section 7.1 says 30 days, but the later amendment Section 12.1 says 180 days.",
        relevant_sections=["Section 7", "Section 12"],
    ),
    EvalTestCase(
        test_id="CONF-005",
        question="What payment timeline applies to large orders over £50,000?",
        contract_id="eval_greenleaf_terra_004",
        category="Payment",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["ninety", "90", "Net 90"],
        ground_truth_answer="Net 90 for orders exceeding £50,000 per Section 11.1 (amendment), superseding the standard Net 45.",
        relevant_sections=["Section 11"],
    ),
]

# ==========================================================================
# UNSUPPORTED / OUT-OF-SCOPE QUESTIONS (5 cases)
# ==========================================================================

UNSUPPORTED_CASES = [
    EvalTestCase(
        test_id="UNSUP-001",
        question="What is the weather forecast for tomorrow in Delaware?",
        contract_id="eval_acme_beta_001",
        category="Unsupported",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_answer_keywords=["not", "contract", "cannot", "outside"],
        expected_absent_keywords=["sunny", "rain", "forecast", "temperature"],
        ground_truth_answer="This question is outside the scope of the contract and cannot be answered from the agreement.",
        relevant_sections=[],
        notes="System should abstain — question is completely unrelated to any contract.",
    ),
    EvalTestCase(
        test_id="UNSUP-002",
        question="What was ACME Corporation's stock price last quarter?",
        contract_id="eval_acme_beta_001",
        category="Unsupported",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_answer_keywords=["not", "contract", "cannot", "insufficient"],
        expected_absent_keywords=["$", "NYSE", "stock"],
        ground_truth_answer="Stock price information is not available in the contract.",
        relevant_sections=[],
    ),
    EvalTestCase(
        test_id="UNSUP-003",
        question="Please draft a counter-proposal for Section 8 termination rights.",
        contract_id="eval_acme_beta_001",
        category="Unsupported",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["Section 8", "terminat"],
        ground_truth_answer="The system can reference Section 8 content but counter-proposals require professional legal drafting.",
        relevant_sections=["Section 8"],
        notes="Partial support — system can ground on Section 8 but shouldn't generate binding legal drafts.",
    ),
    EvalTestCase(
        test_id="UNSUP-004",
        question="Who is the CEO of BetaCorp Solutions?",
        contract_id="eval_acme_beta_001",
        category="Unsupported",
        expected_evidence_status="SUFFICIENT",
        expected_answer_keywords=["Raj Patel", "Managing Director"],
        ground_truth_answer="Raj Patel, Managing Director, signed the agreement for BetaCorp Solutions LLC.",
        relevant_sections=[],
        notes="Answerable from the signature block — edge case.",
    ),
    EvalTestCase(
        test_id="UNSUP-005",
        question="Explain quantum computing and how it relates to this contract.",
        contract_id="eval_acme_beta_001",
        category="Unsupported",
        expected_evidence_status="INSUFFICIENT",
        is_abstention_case=True,
        expected_answer_keywords=["not", "contract", "insufficient", "quantum"],
        expected_absent_keywords=["qubit", "superposition"],
        ground_truth_answer="Quantum computing is not referenced or relevant to this agreement.",
        relevant_sections=[],
    ),
]


# ==========================================================================
# Consolidated test case registry
# ==========================================================================

ALL_TEST_CASES: list = (
    TERMINATION_CASES
    + INDEMNITY_CASES
    + LIABILITY_CASES
    + RENEWAL_CASES
    + PAYMENT_CASES
    + MISSING_CLAUSE_CASES
    + CONFLICT_CASES
    + UNSUPPORTED_CASES
)

TEST_CASES_BY_ID = {tc.test_id: tc for tc in ALL_TEST_CASES}

# Category groupings for reporting
TEST_CASES_BY_CATEGORY = {}
for tc in ALL_TEST_CASES:
    TEST_CASES_BY_CATEGORY.setdefault(tc.category, []).append(tc)
