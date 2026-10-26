import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import analysis, chat, contracts, health, mcp_routes
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ContractLens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure local uploads directory exists
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("ContractLens backend initialized.")
    logger.info(f"Google Gemini Model: {settings.GEMINI_MODEL} (Configured: {settings.is_gemini_configured()})")
    logger.info(f"Google Gemini Embedding Model: {settings.GEMINI_EMBEDDING_MODEL} (Dimension: {settings.GEMINI_EMBEDDING_DIMENSION})")
    logger.info("Storage mode: In-memory FAISS (Zero database dependencies).")
    logger.info(f"Model Context Protocol (MCP): Enabled={settings.MCP_ENABLED}, Transport={settings.MCP_TRANSPORT}")
    yield
    logger.info("ContractLens backend shutting down.")


app = FastAPI(
    title="ContractLens API",
    description="AI-powered Contract Analysis & Risk Intelligence Platform with in-memory FAISS vector RAG and MCP external legal research.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health.router, prefix="/api")
app.include_router(contracts.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(mcp_routes.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Welcome to ContractLens API",
        "documentation": "/docs",
        "health_endpoint": "/api/health",
        "in_memory_faiss": True,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
