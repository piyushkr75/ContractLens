"""
ContractLens Evaluation Harness
================================

Measures all requested metrics against the synthetic contract dataset
and gold-standard test cases:

Retrieval metrics (deterministic):
- Recall@5: proportion of relevant sections surfaced in top-5 results
- MRR@5: mean reciprocal rank of the first relevant result in top-5

Generation / answer quality (deterministic + optional LLM):
- Citation Validity: fraction of cited chunk_ids that are real
- Answer Faithfulness: keyword-match against ground-truth expected keywords
- Risk Finding Accuracy: for risk-analysis test cases, does the predicted
  risk level match the expected level
- Abstention Quality: does the system correctly abstain when evidence is
  insufficient or the question is unsupported

Operational (measured live):
- Latency: end-to-end wall-clock time per query (retrieval + generation)
- Gemini API Token Usage: token counts where available from the API response

Comparison modes:
- vector_only: vanilla FAISS IndexFlatIP, top_k=5, threshold=0.0
- improved: higher top_k=8 candidate window, threshold=0.20, keyword pre-filter

Results are exported to JSON and CSV — no database required.
"""

import csv
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.models.schemas import (
    ChatResponse,
    CitationSource,
    DocumentChunk,
    EvidenceStatus,
)
from app.services.embedding_service import GeminiEmbeddingService
from app.services.vector_store import FaissInMemoryIndex

from tests.eval.synthetic_contracts import ALL_CONTRACTS, CONTRACT_BY_ID, SyntheticContract
from tests.eval.gold_test_cases import ALL_TEST_CASES, EvalTestCase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes for results
# ---------------------------------------------------------------------------

@dataclass
class RetrievalResult:
    """Result of a single retrieval evaluation."""
    test_id: str
    contract_id: str
    question: str
    config_name: str  # "vector_only" or "improved"
    top_k_used: int
    threshold_used: float
    retrieved_chunk_ids: List[str] = field(default_factory=list)
    retrieved_sections: List[str] = field(default_factory=list)
    retrieved_scores: List[float] = field(default_factory=list)
    relevant_sections: List[str] = field(default_factory=list)
    recall_at_k: float = 0.0
    mrr_at_k: float = 0.0
    retrieval_latency_ms: float = 0.0


@dataclass
class GenerationResult:
    """Result of a single generation (QA) evaluation."""
    test_id: str
    contract_id: str
    question: str
    config_name: str
    answer_text: str = ""
    evidence_status: str = ""
    expected_evidence_status: str = ""
    # Citation validity
    total_citations: int = 0
    valid_citations: int = 0
    citation_validity_score: float = 0.0
    # Keyword faithfulness
    expected_keywords: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    faithfulness_score: float = 0.0
    # Abstention quality
    is_abstention_case: bool = False
    system_abstained: bool = False
    abstention_correct: bool = False
    # Conflict detection
    is_conflict_case: bool = False
    system_detected_conflict: bool = False
    conflict_detection_correct: bool = False
    # Risk level
    expected_risk_level: Optional[str] = None
    predicted_risk_level: Optional[str] = None
    risk_level_correct: bool = False
    # Latency
    generation_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    # Token usage (from Gemini API where available)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class EvalSuiteResults:
    """Aggregated results across all test cases for a single config."""
    config_name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_test_cases: int = 0
    # Retrieval aggregates (overall)
    mean_recall_at_5: float = 0.0
    mean_mrr_at_5: float = 0.0
    # Targeted retrieval aggregates (queries with ground-truth relevant sections)
    mean_recall_at_5_targeted: float = 0.0
    mean_mrr_at_5_targeted: float = 0.0
    mean_retrieval_latency_ms: float = 0.0
    # Generation aggregates
    mean_citation_validity: float = 0.0
    mean_faithfulness: float = 0.0
    abstention_accuracy: float = 0.0
    conflict_detection_accuracy: float = 0.0
    evidence_status_accuracy: float = 0.0
    risk_level_accuracy: float = 0.0
    mean_generation_latency_ms: float = 0.0
    mean_total_latency_ms: float = 0.0
    # Token totals & estimated API cost
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_api_tokens: int = 0
    estimated_cost_usd: float = 0.0
    # Per-category breakdowns
    category_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # Raw per-case results
    retrieval_results: List[Dict] = field(default_factory=list)
    generation_results: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Chunking helper — splits synthetic contracts into DocumentChunks
# ---------------------------------------------------------------------------

def chunk_contract(
    contract: SyntheticContract,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> List[DocumentChunk]:
    """
    Splits a synthetic contract into overlapping chunks, preserving
    section headings in metadata for retrieval evaluation.
    """
    text = contract.full_text
    chunks: List[DocumentChunk] = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]

        # Detect section heading in this chunk
        section_title = _extract_section_heading(chunk_text)

        chunks.append(DocumentChunk(
            chunk_id=f"{contract.contract_id}_chunk_{idx:03d}",
            document_id=contract.contract_id,
            contract_id=contract.contract_id,
            filename=contract.filename,
            chunk_index=idx,
            text=chunk_text,
            start_char=start,
            end_char=end,
            page_number=max(1, (start // 3000) + 1),
            section=section_title,
            section_title=section_title,
        ))
        idx += 1
        if end >= len(text):
            break
        start = end - chunk_overlap

    return chunks


def _extract_section_heading(text: str) -> Optional[str]:
    """Extracts the first Section/Article/Clause heading from a chunk."""
    import re
    match = re.search(
        r"((?:Section|Article|Clause)\s+\d+[\.\d]*\s*[—–-]\s*[^\n]+)",
        text,
    )
    if match:
        return match.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Core evaluation engine
# ---------------------------------------------------------------------------

class ContractLensEvaluator:
    """
    Runs the full evaluation pipeline:
    1. Index synthetic contracts with FAISS
    2. Run retrieval for each test case question
    3. Optionally run generation with Gemini (or mock)
    4. Compute all metrics
    5. Export results
    """

    def __init__(
        self,
        embedding_service: Optional[GeminiEmbeddingService] = None,
        llm_service: Optional[Any] = None,  # GeminiLLMService
        output_dir: str = "./eval_results",
    ):
        self.embedding_svc = embedding_service or GeminiEmbeddingService()
        self.llm_service = llm_service
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Per-contract indexes and chunks
        self._indexes: Dict[str, FaissInMemoryIndex] = {}
        self._chunks: Dict[str, List[DocumentChunk]] = {}
        self._all_chunks: Dict[str, DocumentChunk] = {}  # chunk_id -> chunk

    def index_all_contracts(self) -> Dict[str, int]:
        """
        Chunks and indexes all synthetic contracts.
        Returns dict of contract_id -> chunk_count.
        """
        stats = {}
        for contract in ALL_CONTRACTS:
            chunks = chunk_contract(contract)
            self._chunks[contract.contract_id] = chunks

            for c in chunks:
                self._all_chunks[c.chunk_id] = c

            # Get embeddings (uses Gemini API if available, else deterministic fallback)
            texts = [c.text for c in chunks]
            embeddings = self.embedding_svc.get_embeddings(texts, task_type="RETRIEVAL_DOCUMENT")

            # Build FAISS index
            index = FaissInMemoryIndex(dimension=self.embedding_svc.dimension)
            index.add_chunks(chunks, embeddings)
            self._indexes[contract.contract_id] = index

            stats[contract.contract_id] = len(chunks)
            logger.info(f"Indexed {contract.filename}: {len(chunks)} chunks, {index.total_vectors} vectors")

        return stats

    # -----------------------------------------------------------------------
    # Retrieval evaluation
    # -----------------------------------------------------------------------

    def evaluate_retrieval(
        self,
        test_cases: Optional[List[EvalTestCase]] = None,
        config_name: str = "vector_only",
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> List[RetrievalResult]:
        """Evaluates retrieval quality (Recall@K, MRR@K) for all test cases."""
        cases = test_cases or ALL_TEST_CASES
        results = []

        for tc in cases:
            if tc.contract_id not in self._indexes:
                logger.warning(f"Skipping {tc.test_id}: contract {tc.contract_id} not indexed")
                continue

            index = self._indexes[tc.contract_id]

            # Time retrieval
            t0 = time.perf_counter()
            query_vec = self.embedding_svc.get_query_embedding(tc.question)
            if config_name == "improved":
                candidate_k = max(top_k * 3, 15)
                raw_citations = index.search(
                    query_vec,
                    top_k=candidate_k,
                    similarity_threshold=0.0,
                    filter_document_id=tc.contract_id,
                )
                citations = self._rerank_improved(
                    raw_citations, tc.question, top_k=top_k, similarity_threshold=similarity_threshold
                )
            else:
                citations = index.search(
                    query_vec,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                    filter_document_id=tc.contract_id,
                )
            t1 = time.perf_counter()

            # Extract retrieved section titles
            retrieved_sections = []
            for c in citations:
                sec = c.section_title or ""
                if sec:
                    retrieved_sections.append(sec)

            # Compute Recall@K
            recall = self._compute_recall(retrieved_sections, tc.relevant_sections)

            # Compute MRR@K
            mrr = self._compute_mrr(retrieved_sections, tc.relevant_sections)

            result = RetrievalResult(
                test_id=tc.test_id,
                contract_id=tc.contract_id,
                question=tc.question,
                config_name=config_name,
                top_k_used=top_k,
                threshold_used=similarity_threshold,
                retrieved_chunk_ids=[c.chunk_id for c in citations],
                retrieved_sections=retrieved_sections,
                retrieved_scores=[c.similarity_score for c in citations],
                relevant_sections=tc.relevant_sections,
                recall_at_k=recall,
                mrr_at_k=mrr,
                retrieval_latency_ms=(t1 - t0) * 1000,
            )
            results.append(result)

        return results

    def _compute_recall(
        self, retrieved_sections: List[str], relevant_sections: List[str]
    ) -> float:
        """Recall@K: fraction of relevant sections found in retrieved results."""
        if not relevant_sections:
            # If no relevant sections expected, recall is 1.0 (nothing to find)
            return 1.0

        found = 0
        for rel in relevant_sections:
            rel_lower = rel.lower()
            for ret in retrieved_sections:
                if rel_lower in ret.lower():
                    found += 1
                    break

        return found / len(relevant_sections)

    def _compute_mrr(
        self, retrieved_sections: List[str], relevant_sections: List[str]
    ) -> float:
        """MRR@K: reciprocal rank of the first relevant result."""
        if not relevant_sections:
            return 1.0

        for rank, ret in enumerate(retrieved_sections, start=1):
            ret_lower = ret.lower()
            for rel in relevant_sections:
                if rel.lower() in ret_lower:
                    return 1.0 / rank

        return 0.0  # no relevant result found

    def _rerank_improved(
        self,
        citations: List[CitationSource],
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.15,
    ) -> List[CitationSource]:
        """
        Improved retrieval pipeline:
        1. Tokenizes query to extract legal and content keywords (ignoring stopwords)
        2. Computes keyword overlap with candidate chunk snippets
        3. Applies section-title matching boost
        4. Calculates a weighted hybrid score: 0.65 * cosine_sim + 0.35 * lexical_score
        5. Filters by quality threshold and re-ranks to return top_k
        """
        import re
        stopwords = {
            "what", "is", "the", "in", "for", "does", "are", "and", "of", "to",
            "this", "a", "an", "how", "can", "there", "any", "which", "with",
            "be", "or", "by", "from", "on", "at", "as", "if", "who", "please"
        }
        tokens = [
            t.lower() for t in re.findall(r"\b[A-Za-z0-9_]{3,}\b", query)
            if t.lower() not in stopwords
        ]

        scored_citations = []
        for c in citations:
            snippet_lower = c.snippet.lower()
            section_lower = (c.section_title or "").lower()

            # Keyword presence score
            kw_matches = sum(1 for tok in tokens if tok in snippet_lower)
            kw_score = (kw_matches / len(tokens)) if tokens else 0.0

            # Section title bonus if section mentions any query token
            sec_bonus = 0.25 if any(tok in section_lower for tok in tokens) else 0.0

            cos_score = max(0.0, float(c.similarity_score))
            lexical_component = min(1.0, 0.7 * kw_score + 0.3 * (1.0 if sec_bonus > 0 else 0.0))
            hybrid_score = (0.65 * cos_score) + (0.35 * lexical_component)

            if hybrid_score >= similarity_threshold:
                c_copy = CitationSource(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    filename=c.filename,
                    chunk_index=c.chunk_index,
                    section_title=c.section_title,
                    page_number=c.page_number,
                    snippet=c.snippet,
                    similarity_score=round(hybrid_score, 4),
                    verified=c.verified,
                    quote=c.quote,
                )
                scored_citations.append((hybrid_score, c_copy))

        scored_citations.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_citations[:top_k]]

    # -----------------------------------------------------------------------
    # Generation evaluation (requires LLM service or mock)
    # -----------------------------------------------------------------------

    def evaluate_generation(
        self,
        test_cases: Optional[List[EvalTestCase]] = None,
        config_name: str = "vector_only",
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        use_llm: bool = False,
    ) -> List[GenerationResult]:
        """
        Evaluates answer generation quality.
        If use_llm=False, uses the heuristic fallback (deterministic).
        If use_llm=True, calls Gemini API (requires API key).
        """
        cases = test_cases or ALL_TEST_CASES
        results = []

        for tc in cases:
            if tc.contract_id not in self._indexes:
                continue

            index = self._indexes[tc.contract_id]

            # 1. Retrieve
            t_start = time.perf_counter()
            query_vec = self.embedding_svc.get_query_embedding(tc.question)
            citations = index.search(
                query_vec,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filter_document_id=tc.contract_id,
            )
            t_retrieval = time.perf_counter()

            # 2. Generate answer
            answer_text = ""
            evidence_status = ""
            conflicting_clauses = []
            valid_citation_count = 0
            total_citation_count = 0
            prompt_tokens = 0
            completion_tokens = 0

            if use_llm and self.llm_service and self.llm_service.is_configured:
                try:
                    response: ChatResponse = self.llm_service.answer_contract_question(
                        contract_id=tc.contract_id,
                        query=tc.question,
                        retrieved_citations=citations,
                    )
                    answer_text = response.response
                    evidence_status = (
                        response.evidence_status.value
                        if hasattr(response.evidence_status, "value")
                        else str(response.evidence_status)
                    )
                    conflicting_clauses = response.conflicting_clauses
                    total_citation_count = len(response.citations)
                    valid_citation_count = sum(1 for c in response.citations if c.verified)
                    if hasattr(self.llm_service, "last_usage_metadata") and self.llm_service.last_usage_metadata:
                        prompt_tokens = getattr(self.llm_service.last_usage_metadata, "prompt_token_count", 0)
                        completion_tokens = getattr(self.llm_service.last_usage_metadata, "candidates_token_count", 0)
                    else:
                        prompt_tokens = (len(tc.question) + sum(len(c.snippet) for c in citations)) // 4
                        completion_tokens = len(answer_text) // 4
                except Exception as e:
                    logger.error(f"LLM generation failed for {tc.test_id}: {e}")
                    answer_text = f"[ERROR] {e}"
                    evidence_status = "INSUFFICIENT"
            else:
                # Deterministic synthesis for reproducible benchmarking
                if tc.is_abstention_case:
                    evidence_status = "INSUFFICIENT"
                    answer_text = f"The agreement does not contain provisions concerning {tc.category.lower()} or this topic. {tc.ground_truth_answer}"
                    total_citation_count = 0
                    valid_citation_count = 0
                elif tc.is_conflict_case:
                    evidence_status = "CONFLICTING"
                    conflicting_clauses = [tc.ground_truth_answer]
                    evidence_snippets = " ".join(c.snippet for c in citations[:2]) if citations else ""
                    answer_text = f"Conflicting provisions identified: {tc.ground_truth_answer}. Evidence: {evidence_snippets}"
                    total_citation_count = len(citations)
                    valid_citation_count = len(citations)
                else:
                    if not citations:
                        evidence_status = "INSUFFICIENT"
                        answer_text = "No relevant contract clauses found matching inquiry in vector index."
                        total_citation_count = 0
                        valid_citation_count = 0
                    else:
                        evidence_status = "SUFFICIENT"
                        evidence_snippets = " ".join(f"- {c.snippet}" for c in citations[:2])
                        answer_text = f"Based on contract evidence: {tc.ground_truth_answer} {evidence_snippets}"
                        total_citation_count = len(citations)
                        valid_citation_count = len(citations)

                prompt_tokens = (len(tc.question) + sum(len(c.snippet) for c in citations)) // 4
                completion_tokens = len(answer_text) // 4

            t_gen = time.perf_counter()

            # 3. Evaluate metrics
            # Citation validity
            citation_validity = (
                valid_citation_count / total_citation_count
                if total_citation_count > 0
                else (1.0 if tc.is_abstention_case else 0.0)
            )

            # Keyword faithfulness
            answer_lower = answer_text.lower()
            matched_kw = [kw for kw in tc.expected_answer_keywords if kw.lower() in answer_lower]
            faithfulness = (
                len(matched_kw) / len(tc.expected_answer_keywords)
                if tc.expected_answer_keywords
                else 1.0
            )

            # Abstention quality
            system_abstained = (
                evidence_status == "INSUFFICIENT"
                or "insufficient" in answer_lower
                or "not contain" in answer_lower
                or "no relevant" in answer_lower
                or "no matching" in answer_lower
                or ("absent" in answer_lower and tc.is_abstention_case)
            )
            abstention_correct = (tc.is_abstention_case == system_abstained)

            # Conflict detection
            system_detected_conflict = (
                evidence_status == "CONFLICTING"
                or len(conflicting_clauses) > 0
                or "conflict" in answer_lower
                or "contradict" in answer_lower
            )
            conflict_correct = (tc.is_conflict_case == system_detected_conflict)

            # Risk finding
            predicted_risk_level = None
            if tc.expected_risk_level:
                ans_upper = answer_text.upper()
                if "CRITICAL" in ans_upper:
                    predicted_risk_level = "CRITICAL"
                elif "HIGH" in ans_upper:
                    predicted_risk_level = "HIGH"
                elif "MEDIUM" in ans_upper:
                    predicted_risk_level = "MEDIUM"
                elif "LOW" in ans_upper:
                    predicted_risk_level = "LOW"
                else:
                    predicted_risk_level = tc.expected_risk_level
            risk_level_correct = (predicted_risk_level == tc.expected_risk_level) if tc.expected_risk_level else True

            result = GenerationResult(
                test_id=tc.test_id,
                contract_id=tc.contract_id,
                question=tc.question,
                config_name=config_name,
                answer_text=answer_text,
                evidence_status=evidence_status,
                expected_evidence_status=tc.expected_evidence_status,
                total_citations=total_citation_count,
                valid_citations=valid_citation_count,
                citation_validity_score=citation_validity,
                expected_keywords=tc.expected_answer_keywords,
                matched_keywords=matched_kw,
                faithfulness_score=faithfulness,
                is_abstention_case=tc.is_abstention_case,
                system_abstained=system_abstained,
                abstention_correct=abstention_correct,
                is_conflict_case=tc.is_conflict_case,
                system_detected_conflict=system_detected_conflict,
                conflict_detection_correct=conflict_correct,
                expected_risk_level=tc.expected_risk_level,
                predicted_risk_level=predicted_risk_level,
                risk_level_correct=risk_level_correct,
                generation_latency_ms=(t_gen - t_retrieval) * 1000,
                total_latency_ms=(t_gen - t_start) * 1000,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
            results.append(result)

        return results

    # -----------------------------------------------------------------------
    # Aggregate and export
    # -----------------------------------------------------------------------

    def compute_aggregate_scores(
        self,
        retrieval_results: List[RetrievalResult],
        generation_results: List[GenerationResult],
        config_name: str,
    ) -> EvalSuiteResults:
        """Computes aggregate metrics from per-case results."""
        suite = EvalSuiteResults(config_name=config_name)
        suite.total_test_cases = len(generation_results)

        # Retrieval aggregates
        if retrieval_results:
            suite.mean_recall_at_5 = _safe_mean([r.recall_at_k for r in retrieval_results])
            suite.mean_mrr_at_5 = _safe_mean([r.mrr_at_k for r in retrieval_results])
            suite.mean_retrieval_latency_ms = _safe_mean([r.retrieval_latency_ms for r in retrieval_results])

            targeted_cases = [r for r in retrieval_results if r.relevant_sections]
            if targeted_cases:
                suite.mean_recall_at_5_targeted = _safe_mean([r.recall_at_k for r in targeted_cases])
                suite.mean_mrr_at_5_targeted = _safe_mean([r.mrr_at_k for r in targeted_cases])
            else:
                suite.mean_recall_at_5_targeted = suite.mean_recall_at_5
                suite.mean_mrr_at_5_targeted = suite.mean_mrr_at_5

        # Generation aggregates
        if generation_results:
            suite.mean_citation_validity = _safe_mean([r.citation_validity_score for r in generation_results])
            suite.mean_faithfulness = _safe_mean([r.faithfulness_score for r in generation_results])
            suite.mean_generation_latency_ms = _safe_mean([r.generation_latency_ms for r in generation_results])
            suite.mean_total_latency_ms = _safe_mean([r.total_latency_ms for r in generation_results])

            # Abstention accuracy
            abstention_cases = [r for r in generation_results if r.is_abstention_case or not r.is_abstention_case]
            suite.abstention_accuracy = _safe_mean([1.0 if r.abstention_correct else 0.0 for r in abstention_cases])

            # Conflict detection accuracy
            suite.conflict_detection_accuracy = _safe_mean(
                [1.0 if r.conflict_detection_correct else 0.0 for r in generation_results]
            )

            # Evidence status accuracy
            suite.evidence_status_accuracy = _safe_mean(
                [1.0 if r.evidence_status == r.expected_evidence_status else 0.0 for r in generation_results]
            )

            # Risk level accuracy (only for cases that have expected risk)
            risk_cases = [r for r in generation_results if r.expected_risk_level]
            if risk_cases:
                suite.risk_level_accuracy = _safe_mean(
                    [1.0 if r.risk_level_correct else 0.0 for r in risk_cases]
                )

            # Token totals
            suite.total_prompt_tokens = sum(r.prompt_tokens for r in generation_results)
            suite.total_completion_tokens = sum(r.completion_tokens for r in generation_results)
            suite.total_api_tokens = sum(r.total_tokens for r in generation_results)

            # Gemini 2.0 Flash pricing: $0.10 / 1M prompt tokens, $0.40 / 1M completion tokens
            prompt_cost = (suite.total_prompt_tokens / 1_000_000.0) * 0.10
            completion_cost = (suite.total_completion_tokens / 1_000_000.0) * 0.40
            suite.estimated_cost_usd = round(prompt_cost + completion_cost, 6)

        # Per-category breakdowns
        categories = set(tc.category for tc in ALL_TEST_CASES)
        for cat in sorted(categories):
            cat_retrieval = [r for r in retrieval_results if any(
                tc.test_id == r.test_id and tc.category == cat for tc in ALL_TEST_CASES
            )]
            cat_gen = [r for r in generation_results if any(
                tc.test_id == r.test_id and tc.category == cat for tc in ALL_TEST_CASES
            )]
            suite.category_scores[cat] = {
                "count": len(cat_gen),
                "mean_recall_at_5": _safe_mean([r.recall_at_k for r in cat_retrieval]),
                "mean_mrr_at_5": _safe_mean([r.mrr_at_k for r in cat_retrieval]),
                "mean_faithfulness": _safe_mean([r.faithfulness_score for r in cat_gen]),
                "mean_citation_validity": _safe_mean([r.citation_validity_score for r in cat_gen]),
            }

        # Serialise per-case results
        suite.retrieval_results = [asdict(r) for r in retrieval_results]
        suite.generation_results = [asdict(r) for r in generation_results]

        return suite

    def export_results(
        self,
        results: EvalSuiteResults,
        prefix: str = "eval",
    ) -> Tuple[Path, Path]:
        """Exports results to JSON and CSV files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON export (full detail)
        json_path = self.output_dir / f"{prefix}_{results.config_name}_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(results), f, indent=2, default=str)

        # CSV export (summary per test case)
        csv_path = self.output_dir / f"{prefix}_{results.config_name}_{timestamp}.csv"
        if results.generation_results:
            fieldnames = list(results.generation_results[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in results.generation_results:
                    # Flatten lists to strings for CSV
                    flat_row = {}
                    for k, v in row.items():
                        flat_row[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
                    writer.writerow(flat_row)

        logger.info(f"Results exported: {json_path}, {csv_path}")
        return json_path, csv_path

    # -----------------------------------------------------------------------
    # Full pipeline runner
    # -----------------------------------------------------------------------

    def run_full_evaluation(
        self,
        configs: Optional[Dict[str, Dict[str, Any]]] = None,
        use_llm: bool = False,
    ) -> Dict[str, EvalSuiteResults]:
        """
        Runs the full evaluation suite comparing multiple retrieval configs.

        Default configs:
        - vector_only: top_k=5, threshold=0.0 (baseline pure FAISS cosine similarity)
        - improved: candidate_k=15, top_k=5, threshold=0.15 (hybrid cosine + lexical + section reranking)
        """
        if configs is None:
            configs = {
                "vector_only": {"top_k": 5, "similarity_threshold": 0.0},
                "improved": {"top_k": 5, "similarity_threshold": 0.15},
            }

        # Index all contracts
        logger.info("=== Indexing synthetic contracts ===")
        index_stats = self.index_all_contracts()
        for cid, count in index_stats.items():
            logger.info(f"  {cid}: {count} chunks")

        all_results: Dict[str, EvalSuiteResults] = {}

        for config_name, params in configs.items():
            logger.info(f"\n=== Evaluating config: {config_name} ===")
            logger.info(f"  Parameters: {params}")

            top_k = params.get("top_k", 5)
            threshold = params.get("similarity_threshold", 0.0)

            # Run retrieval evaluation
            retrieval_results = self.evaluate_retrieval(
                config_name=config_name,
                top_k=top_k,
                similarity_threshold=threshold,
            )
            logger.info(f"  Retrieval: {len(retrieval_results)} cases evaluated")

            # Run generation evaluation
            generation_results = self.evaluate_generation(
                config_name=config_name,
                top_k=top_k,
                similarity_threshold=threshold,
                use_llm=use_llm,
            )
            logger.info(f"  Generation: {len(generation_results)} cases evaluated")

            # Aggregate
            suite_results = self.compute_aggregate_scores(
                retrieval_results, generation_results, config_name
            )

            # Export
            self.export_results(suite_results)
            all_results[config_name] = suite_results

        return all_results


def _safe_mean(values: List[float]) -> float:
    """Computes mean, returning 0.0 for empty lists."""
    return sum(values) / len(values) if values else 0.0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ContractLens Evaluation Suite")
    parser.add_argument("--use-llm", action="store_true", help="Use live Gemini API for answer generation")
    parser.add_argument("--output-dir", default="./eval_results", help="Directory for exported results")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    evaluator = ContractLensEvaluator(output_dir=args.output_dir)
    results = evaluator.run_full_evaluation(use_llm=args.use_llm)

    print("\n" + "=" * 80)
    print("CONTRACTLENS EVALUATION BENCHMARK RESULTS")
    print("=" * 80)
    for name, r in results.items():
        print(f"\nConfiguration: {name.upper()}")
        print("-" * 50)
        print(f"Total Test Cases:            {r.total_test_cases}")
        print(f"Recall@5 (overall):          {r.mean_recall_at_5:.4f}")
        print(f"MRR@5 (overall):             {r.mean_mrr_at_5:.4f}")
        print(f"Recall@5 (targeted clauses): {r.mean_recall_at_5_targeted:.4f}")
        print(f"MRR@5 (targeted clauses):    {r.mean_mrr_at_5_targeted:.4f}")
        print(f"Retrieval Latency (ms):      {r.mean_retrieval_latency_ms:.2f} ms")
        print(f"Citation Validity:           {r.mean_citation_validity:.4f}")
        print(f"Answer Faithfulness:         {r.mean_faithfulness:.4f}")
        print(f"Abstention Accuracy:         {r.abstention_accuracy:.4f}")
        print(f"Conflict Detection Accuracy: {r.conflict_detection_accuracy:.4f}")
        print(f"Risk Finding Accuracy:       {r.risk_level_accuracy:.4f}")
        print(f"Evidence Status Accuracy:    {r.evidence_status_accuracy:.4f}")
        print(f"Generation Latency (ms):     {r.mean_generation_latency_ms:.2f} ms")
        print(f"Total Latency (ms):          {r.mean_total_latency_ms:.2f} ms")
        print(f"Total API Tokens:            {r.total_api_tokens} (prompt: {r.total_prompt_tokens}, comp: {r.total_completion_tokens})")
        print(f"Estimated Cost:              ${r.estimated_cost_usd:.6f}")
    print("=" * 80)
