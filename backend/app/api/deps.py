from app.config import Settings, settings
from app.core.memory_store import InMemoryContractStore, memory_store
from app.services.embedding_service import GeminiEmbeddingService, embedding_service
from app.services.llm_service import GeminiLLMService, llm_service
from app.services.mcp_service import MCPClientService, mcp_service


def get_settings() -> Settings:
    return settings


def get_memory_store() -> InMemoryContractStore:
    return memory_store


def get_embedding_service() -> GeminiEmbeddingService:
    return embedding_service


def get_llm_service() -> GeminiLLMService:
    return llm_service


def get_mcp_service() -> MCPClientService:
    return mcp_service
