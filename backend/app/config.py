from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration for ContractLens with Google Gemini AI."""

    # Server settings
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Google Gemini API Configuration
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Hosted Gemini Embedding Configuration
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    GEMINI_EMBEDDING_DIMENSION: int = 768

    # Document Upload & In-Memory Chunk Settings
    UPLOAD_DIR: Path = Path("./uploads")
    MAX_FILE_SIZE_MB: int = 25
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # Model Context Protocol (MCP) Configuration for External Legal Web-Search
    MCP_ENABLED: bool = False
    MCP_TRANSPORT: str = "stdio"  # "stdio" or "sse"
    MCP_SERVER_COMMAND: str = "npx"
    MCP_SERVER_ARGS: str = "-y @modelcontextprotocol/server-brave-search"
    MCP_SERVER_URL: Optional[str] = None
    MCP_SERVER_ENV: Optional[str] = None  # JSON string of env vars, e.g. '{"BRAVE_API_KEY":"..."}'
    MCP_ALLOWED_TOOLS: str = "brave_web_search,brave_local_search,duckduckgo_search,web_search,fetch,fetch_page"
    MCP_TIMEOUT_SECONDS: float = 15.0
    MCP_MAX_TOOL_CALLS: int = 3

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def active_gemini_api_key(self) -> Optional[str]:
        key = self.GEMINI_API_KEY or self.GOOGLE_API_KEY
        if key and not key.startswith("your_"):
            return key
        return None

    def is_gemini_configured(self) -> bool:
        return self.active_gemini_api_key is not None

    @property
    def mcp_args_list(self) -> List[str]:
        import shlex
        if not self.MCP_SERVER_ARGS:
            return []
        try:
            return shlex.split(self.MCP_SERVER_ARGS, posix=False)
        except Exception:
            return self.MCP_SERVER_ARGS.split()

    @property
    def mcp_allowed_tools_set(self) -> set:
        return {
            t.strip()
            for t in self.MCP_ALLOWED_TOOLS.split(",")
            if t.strip()
        }

    @property
    def mcp_env_dict(self) -> dict:
        import json
        if not self.MCP_SERVER_ENV:
            return {}
        try:
            parsed = json.loads(self.MCP_SERVER_ENV)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            pass
        return {}

    def is_mcp_configured(self) -> bool:
        return bool(self.MCP_ENABLED and (self.MCP_SERVER_COMMAND or self.MCP_SERVER_URL))


settings = Settings()
