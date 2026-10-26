from fastapi import APIRouter, Depends
from app.api.deps import get_memory_store, get_settings
from app.config import Settings
from app.core.memory_store import InMemoryContractStore
from app.models.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
def get_health_status(
    settings: Settings = Depends(get_settings),
    store: InMemoryContractStore = Depends(get_memory_store),
):
    """
    Health check endpoint returning system status, active configuration flags,
    and in-memory FAISS vector index stats.
    """
    stats = store.get_stats()
    is_gemini_ok = settings.is_gemini_configured()
    return HealthResponse(
        status="healthy",
        app_name="ContractLens API",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        uptime_seconds=stats["uptime_seconds"],
        ai_provider="Google Gemini",
        gemini_model=settings.GEMINI_MODEL,
        llm_configured=is_gemini_ok,
        embedding_configured=is_gemini_ok,
        mcp_enabled=settings.MCP_ENABLED,
        mcp_transport=settings.MCP_TRANSPORT,
        mcp_configured=settings.is_mcp_configured(),
        mcp_server_command=settings.MCP_SERVER_COMMAND if settings.MCP_TRANSPORT == "stdio" else settings.MCP_SERVER_URL,
        in_memory_documents_count=stats["in_memory_documents_count"],
        faiss_indexes_count=stats["faiss_indexes_count"],
    )
