from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_embedding_service, get_llm_service, get_memory_store
from app.core.memory_store import InMemoryContractStore
from app.models.schemas import (
    AnalyzeRequest,
    CompareContractsRequest,
    ContractAnalysisResponse,
    ContractComparisonResponse,
)
from app.services.embedding_service import GeminiEmbeddingService
from app.services.llm_service import GeminiLLMService

router = APIRouter(prefix="/contracts", tags=["Analysis"])


@router.post("/{contract_id}/analyze", response_model=ContractAnalysisResponse)
def trigger_analysis(
    contract_id: str,
    payload: Optional[AnalyzeRequest] = None,
    store: InMemoryContractStore = Depends(get_memory_store),
    llm: GeminiLLMService = Depends(get_llm_service),
    embedding_svc: GeminiEmbeddingService = Depends(get_embedding_service),
):
    """
    Executes deep legal risk intelligence analysis on the contract using hosted Google Gemini.
    Stores the structured risk assessment and clause breakdowns in memory.
    """
    contract = store.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found in memory.")

    chunks = store.get_chunks(contract_id)
    faiss_index = store.get_vector_index(contract_id)
    review_policy = payload.review_policy if payload else None

    # Run analysis
    analysis = llm.analyze_contract(
        contract_id=contract_id,
        filename=contract["filename"],
        contract_text=contract["raw_text"],
        chunks=chunks,
        faiss_index=faiss_index,
        embedding_svc=embedding_svc,
        review_policy=review_policy,
    )

    # Store analysis in memory
    store.save_analysis(contract_id, analysis)
    return analysis


@router.get("/{contract_id}/analysis", response_model=ContractAnalysisResponse)
def get_analysis(
    contract_id: str,
    store: InMemoryContractStore = Depends(get_memory_store),
    llm: GeminiLLMService = Depends(get_llm_service),
    embedding_svc: GeminiEmbeddingService = Depends(get_embedding_service),
):
    """
    Retrieves previously computed risk analysis from memory.
    If not yet analyzed, automatically triggers and caches the analysis.
    """
    analysis = store.get_analysis(contract_id)
    if analysis:
        return analysis

    # Auto-trigger if contract exists
    contract = store.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found in memory.")

    chunks = store.get_chunks(contract_id)
    faiss_index = store.get_vector_index(contract_id)

    analysis = llm.analyze_contract(
        contract_id=contract_id,
        filename=contract["filename"],
        contract_text=contract["raw_text"],
        chunks=chunks,
        faiss_index=faiss_index,
        embedding_svc=embedding_svc,
        review_policy=None,
    )
    store.save_analysis(contract_id, analysis)
    return analysis


@router.post("/compare", response_model=ContractComparisonResponse)
def compare_contracts_endpoint(
    payload: CompareContractsRequest,
    store: InMemoryContractStore = Depends(get_memory_store),
    llm: GeminiLLMService = Depends(get_llm_service),
    embedding_svc: GeminiEmbeddingService = Depends(get_embedding_service),
):
    """
    Compares two contracts loaded in the current in-memory session.
    Retrieves relevant sections from each agreement, matches clauses across categories,
    verifies citations, highlights differences, and provides human review rationale
    without declaring legal superiority.
    """
    if payload.contract_a_id == payload.contract_b_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a contract with itself. Please select two distinct contracts.",
        )

    contract_a = store.get_contract(payload.contract_a_id)
    if not contract_a:
        raise HTTPException(
            status_code=404,
            detail=f"Contract A '{payload.contract_a_id}' not found in in-memory session.",
        )

    contract_b = store.get_contract(payload.contract_b_id)
    if not contract_b:
        raise HTTPException(
            status_code=404,
            detail=f"Contract B '{payload.contract_b_id}' not found in in-memory session.",
        )

    chunks_a = store.get_chunks(payload.contract_a_id)
    faiss_a = store.get_vector_index(payload.contract_a_id)
    chunks_b = store.get_chunks(payload.contract_b_id)
    faiss_b = store.get_vector_index(payload.contract_b_id)

    comparison = llm.compare_contracts(
        contract_a_id=payload.contract_a_id,
        contract_a_filename=contract_a["filename"],
        contract_a_text=contract_a["raw_text"],
        contract_a_chunks=chunks_a,
        contract_a_faiss=faiss_a,
        contract_b_id=payload.contract_b_id,
        contract_b_filename=contract_b["filename"],
        contract_b_text=contract_b["raw_text"],
        contract_b_chunks=chunks_b,
        contract_b_faiss=faiss_b,
        embedding_svc=embedding_svc,
        focus_categories=payload.focus_categories,
    )

    cache_key = f"{payload.contract_a_id}:{payload.contract_b_id}"
    store.save_comparison(cache_key, comparison)
    return comparison


@router.get("/compare/{contract_a_id}/{contract_b_id}", response_model=ContractComparisonResponse)
def get_or_compare_contracts(
    contract_a_id: str,
    contract_b_id: str,
    store: InMemoryContractStore = Depends(get_memory_store),
    llm: GeminiLLMService = Depends(get_llm_service),
    embedding_svc: GeminiEmbeddingService = Depends(get_embedding_service),
):
    """
    Retrieves or generates comparative risk intelligence between two contracts.
    """
    if contract_a_id == contract_b_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a contract with itself. Please select two distinct contracts.",
        )

    cache_key = f"{contract_a_id}:{contract_b_id}"
    cached = store.get_comparison(cache_key)
    if cached:
        return cached

    # Otherwise trigger comparison
    req = CompareContractsRequest(contract_a_id=contract_a_id, contract_b_id=contract_b_id)
    return compare_contracts_endpoint(req, store=store, llm=llm, embedding_svc=embedding_svc)

