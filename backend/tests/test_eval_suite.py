"""
ContractLens Evaluation Suite Unit Tests
==========================================

Deterministic test suite verifying the reproducible evaluation pipeline:
- Synthetic contract integrity and clause coverage
- Gold-standard test cases coverage across 8 categories
- FAISS chunking, indexing, and retrieval mechanics
- Retrieval metrics (Recall@5, MRR@5) computation
- Improved retrieval configuration (hybrid candidate reranking)
- Generation metrics: citation validity, faithfulness, abstention, conflict detection, risk accuracy
- End-to-end evaluation runner with JSON and CSV exports
"""

import csv
import json
from pathlib import Path
import numpy as np
import pytest

from app.models.schemas import CitationSource, DocumentChunk
from tests.eval.synthetic_contracts import (
    ALL_CONTRACTS,
    CONTRACT_BY_ID,
    CONTRACT_ACME_BETA,
    CONTRACT_OMEGA_SIGMA,
    CONTRACT_DELTA_EPSILON,
    CONTRACT_GREENLEAF_TERRA,
    CONTRACT_NOVAHEALTH_MEDICORE,
)
from tests.eval.gold_test_cases import (
    ALL_TEST_CASES,
    TEST_CASES_BY_ID,
    TEST_CASES_BY_CATEGORY,
    TERMINATION_CASES,
    INDEMNITY_CASES,
    LIABILITY_CASES,
    RENEWAL_CASES,
    PAYMENT_CASES,
    MISSING_CLAUSE_CASES,
    CONFLICT_CASES,
    UNSUPPORTED_CASES,
)
from tests.eval.eval_harness import (
    ContractLensEvaluator,
    GenerationResult,
    RetrievalResult,
    chunk_contract,
    _safe_mean,
)


class TestSyntheticContractsDataset:
    """Verifies the synthetic contract dataset structure, metadata, and clause integrity."""

    def test_all_five_contracts_present(self):
        assert len(ALL_CONTRACTS) == 5
        expected_ids = {
            "eval_acme_beta_001",
            "eval_omega_sigma_002",
            "eval_delta_epsilon_003",
            "eval_greenleaf_terra_004",
            "eval_novahealth_medicore_005",
        }
        assert set(CONTRACT_BY_ID.keys()) == expected_ids

    def test_contracts_have_valid_text_and_metadata(self):
        for c in ALL_CONTRACTS:
            assert len(c.full_text) > 500, f"{c.contract_id} text is too short"
            assert c.filename.endswith(".pdf")
            assert len(c.jurisdiction) > 0
            assert len(c.title) > 0

    def test_acme_beta_is_balanced_and_complete(self):
        acme = CONTRACT_ACME_BETA
        assert len(acme.present_clauses) >= 8
        assert len(acme.absent_clauses) == 0
        assert len(acme.conflicting_clauses) == 0

    def test_omega_sigma_has_expected_omissions(self):
        omega = CONTRACT_OMEGA_SIGMA
        assert "Liability Limits" in omega.absent_clauses
        assert "Data Protection" in omega.absent_clauses

    def test_greenleaf_terra_has_conflicting_clauses(self):
        greenleaf = CONTRACT_GREENLEAF_TERRA
        assert "Termination" in greenleaf.conflicting_clauses
        assert "Payment" in greenleaf.conflicting_clauses


class TestGoldTestCasesCoverage:
    """Verifies that the test case suite meets all specification requirements."""

    def test_total_count_within_specification_range(self):
        # Spec requires 30–50 test cases
        assert 30 <= len(ALL_TEST_CASES) <= 50
        assert len(ALL_TEST_CASES) == 40

    def test_unique_test_case_ids(self):
        ids = [tc.test_id for tc in ALL_TEST_CASES]
        assert len(ids) == len(set(ids)), "Test case IDs must be unique"

    def test_all_clause_categories_covered(self):
        assert len(TERMINATION_CASES) >= 6
        assert len(INDEMNITY_CASES) >= 5
        assert len(LIABILITY_CASES) >= 5
        assert len(RENEWAL_CASES) >= 4
        assert len(PAYMENT_CASES) >= 5
        assert len(MISSING_CLAUSE_CASES) >= 5
        assert len(CONFLICT_CASES) >= 5
        assert len(UNSUPPORTED_CASES) >= 5

    def test_abstention_cases_properly_flagged(self):
        abstention_cases = [tc for tc in ALL_TEST_CASES if tc.is_abstention_case]
        assert len(abstention_cases) >= 8
        for tc in abstention_cases:
            assert tc.expected_evidence_status == "INSUFFICIENT"

    def test_conflict_cases_properly_flagged(self):
        conflict_cases = [tc for tc in ALL_TEST_CASES if tc.is_conflict_case]
        assert len(conflict_cases) >= 5
        for tc in conflict_cases:
            assert tc.expected_evidence_status == "CONFLICTING"

    def test_risk_level_annotations_present(self):
        risk_cases = [tc for tc in ALL_TEST_CASES if tc.expected_risk_level]
        assert len(risk_cases) >= 10
        valid_levels = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        for tc in risk_cases:
            assert tc.expected_risk_level in valid_levels


class TestChunkingAndIndexing:
    """Verifies chunking without infinite loops and in-memory FAISS indexing."""

    def test_chunking_terminates_and_preserves_sections(self):
        for contract in ALL_CONTRACTS:
            chunks = chunk_contract(contract, chunk_size=800, chunk_overlap=120)
            assert len(chunks) > 0
            # Every chunk must have a non-empty text and correct document_id
            for c in chunks:
                assert len(c.text) > 0
                assert c.document_id == contract.contract_id
                assert c.chunk_id.startswith(contract.contract_id)

    def test_evaluator_indexes_all_synthetic_contracts(self):
        evaluator = ContractLensEvaluator()
        stats = evaluator.index_all_contracts()
        assert len(stats) == 5
        for cid, count in stats.items():
            assert count >= 5
            assert evaluator._indexes[cid].total_vectors == count


class TestMetricsCalculation:
    """Verifies accurate calculation of Recall@K, MRR@K, Faithfulness, and Citation Validity."""

    @pytest.fixture
    def evaluator(self):
        evaluator = ContractLensEvaluator()
        evaluator.index_all_contracts()
        return evaluator

    def test_recall_at_k_calculation(self, evaluator):
        relevant = ["Section 8", "Section 10"]
        # Perfectly retrieved
        retrieved_perfect = ["Section 8 — Termination", "Section 10 — Indemnification", "Section 5"]
        assert evaluator._compute_recall(retrieved_perfect, relevant) == 1.0

        # Partial retrieved (1 of 2)
        retrieved_partial = ["Section 8 — Termination", "Section 5", "Section 1"]
        assert evaluator._compute_recall(retrieved_partial, relevant) == 0.5

        # None retrieved
        retrieved_none = ["Section 1", "Section 2"]
        assert evaluator._compute_recall(retrieved_none, relevant) == 0.0

        # Empty relevant sections (abstention cases) defaults to 1.0
        assert evaluator._compute_recall(retrieved_none, []) == 1.0

    def test_mrr_at_k_calculation(self, evaluator):
        relevant = ["Section 8"]
        # First position -> rank 1 -> 1.0
        assert evaluator._compute_mrr(["Section 8 — Termination", "Section 10"], relevant) == 1.0

        # Second position -> rank 2 -> 0.5
        assert evaluator._compute_mrr(["Section 1", "Section 8 — Termination"], relevant) == 0.5

        # Third position -> rank 3 -> 0.3333
        assert np.isclose(
            evaluator._compute_mrr(["Section 1", "Section 2", "Section 8 — Termination"], relevant),
            1.0 / 3.0,
        )

        # Not found -> 0.0
        assert evaluator._compute_mrr(["Section 1", "Section 2"], relevant) == 0.0

    def test_safe_mean_helper(self):
        assert _safe_mean([]) == 0.0
        assert _safe_mean([1.0, 2.0, 3.0]) == 2.0


class TestRetrievalConfigurationsComparison:
    """Verifies comparison between vector-only and improved retrieval configurations."""

    @pytest.fixture
    def evaluator(self):
        evaluator = ContractLensEvaluator()
        evaluator.index_all_contracts()
        return evaluator

    def test_vector_only_retrieval_runs_and_measures_recall_mrr(self, evaluator):
        results = evaluator.evaluate_retrieval(config_name="vector_only", top_k=5, similarity_threshold=0.0)
        assert len(results) == len(ALL_TEST_CASES)
        for r in results:
            assert isinstance(r, RetrievalResult)
            assert 0.0 <= r.recall_at_k <= 1.0
            assert 0.0 <= r.mrr_at_k <= 1.0
            assert r.retrieval_latency_ms >= 0.0
            assert r.config_name == "vector_only"

    def test_improved_retrieval_demonstrates_higher_or_equal_mrr(self, evaluator):
        res_vector = evaluator.evaluate_retrieval(config_name="vector_only", top_k=5, similarity_threshold=0.0)
        res_improved = evaluator.evaluate_retrieval(config_name="improved", top_k=5, similarity_threshold=0.15)

        mrr_vector = _safe_mean([r.mrr_at_k for r in res_vector])
        mrr_improved = _safe_mean([r.mrr_at_k for r in res_improved])

        # Improved hybrid configuration should achieve higher or equal MRR
        assert mrr_improved >= mrr_vector

    def test_improved_reranker_prioritizes_keyword_and_section_matches(self, evaluator):
        dummy_citations = [
            CitationSource(
                chunk_id="c1",
                document_id="doc1",
                filename="doc1.pdf",
                chunk_index=0,
                section_title="General Definitions",
                snippet="General terms and definitions of words.",
                similarity_score=0.40,
                verified=True,
            ),
            CitationSource(
                chunk_id="c2",
                document_id="doc1",
                filename="doc1.pdf",
                chunk_index=1,
                section_title="Section 8 — Termination",
                snippet="Either party may terminate for convenience upon ninety 90 days notice.",
                similarity_score=0.35,
                verified=True,
            ),
        ]
        reranked = evaluator._rerank_improved(
            dummy_citations,
            query="What is the notice period for termination for convenience?",
            top_k=2,
            similarity_threshold=0.10,
        )
        assert len(reranked) == 2
        # c2 must be ranked first due to section title and keyword boost
        assert reranked[0].chunk_id == "c2"


class TestGenerationAndRiskEvaluation:
    """Verifies generation evaluation metrics: citation validity, faithfulness, abstention, conflict, risk."""

    @pytest.fixture
    def evaluator(self):
        evaluator = ContractLensEvaluator()
        evaluator.index_all_contracts()
        return evaluator

    def test_deterministic_generation_evaluation(self, evaluator):
        gen_results = evaluator.evaluate_generation(
            config_name="vector_only",
            top_k=5,
            similarity_threshold=0.0,
            use_llm=False,
        )
        assert len(gen_results) == len(ALL_TEST_CASES)

        for r in gen_results:
            assert isinstance(r, GenerationResult)
            assert 0.0 <= r.citation_validity_score <= 1.0
            assert 0.0 <= r.faithfulness_score <= 1.0
            assert r.generation_latency_ms >= 0.0
            assert r.total_tokens > 0

    def test_abstention_cases_correctly_handled(self, evaluator):
        gen_results = evaluator.evaluate_generation(
            config_name="vector_only",
            top_k=5,
            similarity_threshold=0.0,
            use_llm=False,
        )
        abstention_results = [r for r in gen_results if r.is_abstention_case]
        assert len(abstention_results) >= 8
        for r in abstention_results:
            assert r.abstention_correct is True
            assert r.evidence_status == "INSUFFICIENT"
            assert r.citation_validity_score == 1.0  # Zero invalid citations fabricated

    def test_conflict_cases_correctly_detected(self, evaluator):
        gen_results = evaluator.evaluate_generation(
            config_name="vector_only",
            top_k=5,
            similarity_threshold=0.0,
            use_llm=False,
        )
        conflict_results = [r for r in gen_results if r.is_conflict_case]
        assert len(conflict_results) >= 5
        for r in conflict_results:
            assert r.conflict_detection_correct is True
            assert r.evidence_status == "CONFLICTING"

    def test_risk_finding_accuracy(self, evaluator):
        gen_results = evaluator.evaluate_generation(
            config_name="vector_only",
            top_k=5,
            similarity_threshold=0.0,
            use_llm=False,
        )
        risk_results = [r for r in gen_results if r.expected_risk_level]
        assert len(risk_results) >= 10
        correct_count = sum(1 for r in risk_results if r.risk_level_correct)
        accuracy = correct_count / len(risk_results)
        assert accuracy >= 0.80, f"Expected risk finding accuracy >= 80%, got {accuracy:.2f}"


class TestEndToEndHarnessRunnerAndExport:
    """Verifies full benchmark execution and JSON/CSV export without a database."""

    def test_full_evaluation_produces_exported_files(self, tmp_path):
        evaluator = ContractLensEvaluator(output_dir=str(tmp_path))
        results = evaluator.run_full_evaluation(use_llm=False)

        assert "vector_only" in results
        assert "improved" in results

        for config_name in ["vector_only", "improved"]:
            res = results[config_name]
            assert res.total_test_cases == 40
            assert res.mean_recall_at_5 > 0.60
            assert res.mean_mrr_at_5 > 0.50
            assert res.mean_citation_validity == 1.0
            assert res.abstention_accuracy == 1.0
            assert res.risk_level_accuracy >= 0.80
            assert res.total_api_tokens > 10000
            assert res.estimated_cost_usd > 0.0

            # Verify exported JSON
            json_files = list(tmp_path.glob(f"eval_{config_name}_*.json"))
            assert len(json_files) == 1
            with open(json_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                assert data["config_name"] == config_name
                assert len(data["retrieval_results"]) == 40
                assert len(data["generation_results"]) == 40
                assert "estimated_cost_usd" in data

            # Verify exported CSV
            csv_files = list(tmp_path.glob(f"eval_{config_name}_*.csv"))
            assert len(csv_files) == 1
            with open(csv_files[0], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 40
                assert "test_id" in rows[0]
                assert "faithfulness_score" in rows[0]
                assert "citation_validity_score" in rows[0]
