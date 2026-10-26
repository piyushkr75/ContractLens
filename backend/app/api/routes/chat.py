from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import (
    get_embedding_service,
    get_llm_service,
    get_mcp_service,
    get_memory_store,
)
from app.core.memory_store import InMemoryContractStore
from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from app.services.embedding_service import GeminiEmbeddingService
from app.services.llm_service import GeminiLLMService
from app.services.mcp_service import MCPClientService

router = APIRouter(prefix="/contracts", tags=["RAG Chat"])


@router.post("/{contract_id}/chat", response_model=ChatResponse)
async def chat_with_contract(
    contract_id: str,
    payload: ChatRequest,
    store: InMemoryContractStore = Depends(get_memory_store),
    embedding_svc: GeminiEmbeddingService = Depends(get_embedding_service),
    llm: GeminiLLMService = Depends(get_llm_service),
    mcp_svc: MCPClientService = Depends(get_mcp_service),
):
    """
    RAG-powered conversational endpoint with MCP external legal research.
    Performs vector similarity search on the contract's in-memory FAISS index
    and generates legally grounded answers with clause citations and external research.
    """
    contract = store.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found in memory.")

    faiss_index = store.get_vector_index(contract_id)
    if not faiss_index:
        raise HTTPException(
            status_code=400,
            detail="FAISS vector index not initialized for this contract.",
        )

    # 1. Embed query
    query_vector = embedding_svc.get_query_embedding(payload.message)

    # 2. Vector search via in-memory FAISS with threshold and session filtering
    citations = faiss_index.search(
        query_vector,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
        filter_document_id=payload.filter_document_id or contract_id,
    )

    # 3. Get existing thread history from payload or memory
    history = payload.history or store.get_chat_history(contract_id)

    # 4. Generate structured, verified QA response with research mode
    chat_response = await llm.answer_contract_question_async(
        contract_id=contract_id,
        query=payload.message,
        retrieved_citations=citations,
        history=history,
        research_mode=payload.research_mode,
        mcp_svc=mcp_svc,
    )

    # 5. Persist to memory store chat history
    store.append_chat_message(
        contract_id, ChatMessage(role="user", content=payload.message)
    )
    store.append_chat_message(
        contract_id, ChatMessage(role="assistant", content=chat_response.response)
    )

    return chat_response


@router.get("/{contract_id}/chat/history", response_model=List[ChatMessage])
def get_chat_history(
    contract_id: str,
    store: InMemoryContractStore = Depends(get_memory_store),
):
    """Retrieves in-memory conversation history for this contract."""
    contract = store.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found in memory.")
    return store.get_chat_history(contract_id)
