from fastapi import APIRouter, Depends
from app.api.deps import get_mcp_service
from app.services.mcp_service import MCPClientService

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol"])


@router.get("/status")
async def get_mcp_status(mcp_svc: MCPClientService = Depends(get_mcp_service)):
    """
    Returns MCP connection diagnostics, active transport, and discovered tools.
    """
    return await mcp_svc.test_connection()
