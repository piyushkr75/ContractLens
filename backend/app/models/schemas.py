from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HealthResponse(BaseModel):
    status: str = "healthy"
    app_name: str = "ContractLens API"
    version: str = "1.0.0"
    environment: str
    uptime_seconds: float
    ai_provider: str = "Google Gemini"
    gemini_model: str
    llm_configured: bool
    embedding_configured: bool
    mcp_enabled: bool = False
    mcp_transport: str = "stdio"
    mcp_configured: bool = False
    mcp_server_command: Optional[str] = None
    in_memory_documents_count: int
    faiss_indexes_count: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    contract_id: Optional[str] = None
    filename: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    section_title: Optional[str] = None
    char_count: int = 0
    word_count: int = 0

    def model_post_init(self, __context: Any) -> None:
        if not self.contract_id:
            self.contract_id = self.document_id
        if not self.section_title:
            self.section_title = self.section
        if not self.char_count:
            self.char_count = len(self.text)
        if not self.word_count:
            self.word_count = len(self.text.split())


class ContractUploadResponse(BaseModel):
    contract_id: str
    filename: str
    file_size_bytes: int
    total_characters: int
    total_chunks: int
    uploaded_at: datetime
    message: str


class ContractSummary(BaseModel):
    contract_id: str
    filename: str
    file_size_bytes: int
    uploaded_at: datetime
    total_chunks: int
    analyzed: bool
    overall_risk_score: Optional[int] = None
    overall_risk_level: Optional[RiskLevel] = None


class ClausePresenceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    RETRIEVAL_FAILED_TO_FIND = "RETRIEVAL_FAILED_TO_FIND"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICTING = "CONFLICTING"


class ClauseAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str  # e.g., "Termination", "Indemnification", "Liability Limits", etc.
    clause_title: str
    presence_status: ClausePresenceStatus = ClausePresenceStatus.PRESENT
    review_priority: RiskLevel = RiskLevel.MEDIUM
    cited_chunk_id: Optional[str] = None
    cited_evidence: Optional[str] = None
    explanation: str
    policy_mismatch: Optional[str] = None
    missing_information: Optional[str] = None
    suggested_questions: List[str] = []
    suggested_revision: Optional[str] = None

    # Backward compatibility with existing UI components:
    original_text: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_score: int = Field(default=50, ge=0, le=100)
    risk_reasoning: str = ""
    mitigation_recommendation: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.original_text:
            self.original_text = self.cited_evidence or (
                f"[{self.presence_status.value}] No direct clause text located in contract."
            )
        if not self.risk_reasoning:
            self.risk_reasoning = self.explanation
        if not self.mitigation_recommendation:
            if self.suggested_questions:
                self.mitigation_recommendation = "Review Questions: " + "; ".join(self.suggested_questions)
            elif self.policy_mismatch:
                self.mitigation_recommendation = f"Policy Alignment: {self.policy_mismatch}"
            else:
                self.mitigation_recommendation = "Verify clause terms against baseline commercial standards."
        self.risk_level = self.review_priority


class RiskCategoryBreakdown(BaseModel):
    category: str
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    clauses_flagged: int


class AnalyzeRequest(BaseModel):
    review_policy: Optional[str] = None


class RawClauseRiskAnalysis(BaseModel):
    category: str
    clause_title: str
    presence_status: ClausePresenceStatus = ClausePresenceStatus.PRESENT
    review_priority: RiskLevel = RiskLevel.MEDIUM
    cited_chunk_id: Optional[str] = None
    cited_evidence: Optional[str] = None
    explanation: str
    policy_mismatch: Optional[str] = None
    missing_information: Optional[str] = None
    suggested_questions: List[str] = []
    suggested_revision: Optional[str] = None
    risk_score: Optional[int] = None


class RawContractRiskResponse(BaseModel):
    overall_risk_score: int = Field(default=50, ge=0, le=100)
    overall_risk_level: RiskLevel = RiskLevel.MEDIUM
    executive_summary: str
    key_vulnerabilities: List[str] = []
    clauses: List[RawClauseRiskAnalysis] = []


class ContractAnalysisResponse(BaseModel):
    contract_id: str
    filename: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_risk_score: int = Field(ge=0, le=100)
    overall_risk_level: RiskLevel
    executive_summary: str
    key_vulnerabilities: List[str]
    review_policy_used: Optional[str] = None
    legal_disclaimer: str = (
        "Automated risk intelligence provided for review assistance only. "
        "Does not constitute legal advice."
    )
    category_breakdowns: List[RiskCategoryBreakdown]
    clauses: List[ClauseAnalysis]


class EvidenceStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"


class CitationSource(BaseModel):
    chunk_id: str
    document_id: Optional[str] = None
    filename: Optional[str] = None
    chunk_index: int
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    snippet: str
    similarity_score: float
    verified: bool = True
    quote: Optional[str] = None


class RawLLMCitation(BaseModel):
    chunk_id: str
    quote: Optional[str] = None
    reason: Optional[str] = None


class RawLLMQAResponse(BaseModel):
    answer: str
    evidence_status: EvidenceStatus = EvidenceStatus.SUFFICIENT
    conflicting_clauses: List[str] = []
    limitations: List[str] = []
    citations: List[RawLLMCitation] = []
    contract_findings: Optional[str] = None
    external_findings: Optional[str] = None
    legal_implications: Optional[str] = None
    uncertainties_and_advice: Optional[str] = None


class ResearchMode(str, Enum):
    DOCUMENT_ONLY = "document_only"
    EXTERNAL_RESEARCH = "external_research"
    AUTO = "auto"


class ExternalSearchStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    SUCCESS = "SUCCESS"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"
    NO_RESULTS = "NO_RESULTS"


class ExternalSource(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None
    publication_date: Optional[str] = None
    source_type: Optional[str] = None  # "Statute", "Judiciary", "Regulatory", "Legal Analysis", "Web"
    verified: bool = True


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    top_k: int = 4
    similarity_threshold: float = 0.0
    filter_document_id: Optional[str] = None
    research_mode: ResearchMode = ResearchMode.DOCUMENT_ONLY


class ChatResponse(BaseModel):
    contract_id: str
    response: str
    evidence_status: EvidenceStatus = EvidenceStatus.SUFFICIENT
    conflicting_clauses: List[str] = []
    limitations: List[str] = []
    citations: List[CitationSource]
    research_mode: ResearchMode = ResearchMode.DOCUMENT_ONLY
    external_research_used: bool = False
    external_search_status: ExternalSearchStatus = ExternalSearchStatus.NOT_REQUESTED
    external_sources: List[ExternalSource] = []
    contract_findings: Optional[str] = None
    external_findings: Optional[str] = None
    legal_implications: Optional[str] = None
    uncertainties_and_advice: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CompareContractsRequest(BaseModel):
    contract_a_id: str
    contract_b_id: str
    focus_categories: Optional[List[str]] = None


class ContractClauseEvidence(BaseModel):
    contract_id: str
    filename: str
    presence_status: ClausePresenceStatus = ClausePresenceStatus.PRESENT
    cited_chunk_id: Optional[str] = None
    cited_evidence: Optional[str] = None
    summary: Optional[str] = None
    citation: Optional[CitationSource] = None


class ClauseComparison(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    clause_title: str
    contract_a: ContractClauseEvidence
    contract_b: ContractClauseEvidence
    difference_summary: str
    human_review_rationale: str
    suggested_questions: List[str] = []
    review_significance: RiskLevel = RiskLevel.MEDIUM


class ContractComparisonResponse(BaseModel):
    comparison_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contract_a_id: str
    contract_a_filename: str
    contract_b_id: str
    contract_b_filename: str
    compared_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executive_summary: str
    key_differences: List[str] = []
    clauses: List[ClauseComparison]
    legal_disclaimer: str = (
        "Automated contract comparison provided for review assistance only. "
        "Does not constitute legal advice and does not declare either agreement legally superior."
    )


class RawClauseComparison(BaseModel):
    category: str
    clause_title: Optional[str] = None
    contract_a_presence: ClausePresenceStatus = ClausePresenceStatus.PRESENT
    contract_a_chunk_id: Optional[str] = None
    contract_a_evidence: Optional[str] = None
    contract_a_summary: Optional[str] = None
    contract_b_presence: ClausePresenceStatus = ClausePresenceStatus.PRESENT
    contract_b_chunk_id: Optional[str] = None
    contract_b_evidence: Optional[str] = None
    contract_b_summary: Optional[str] = None
    difference_summary: str
    human_review_rationale: str
    suggested_questions: List[str] = []
    review_significance: RiskLevel = RiskLevel.MEDIUM


class RawContractComparisonResponse(BaseModel):
    executive_summary: str
    key_differences: List[str] = []
    clauses: List[RawClauseComparison] = []

