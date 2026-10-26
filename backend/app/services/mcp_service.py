import asyncio
import json
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple

import jsonschema
from google.genai import types

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from app.config import settings
from app.models.schemas import ExternalSearchStatus, ExternalSource

logger = logging.getLogger(__name__)


# SSRF Protection: Block loopback and standard private IP spaces
BLOCKED_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
PRIVATE_IP_PREFIXES = (
    "10.",
    "192.168.",
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "169.254.",
)


def is_safe_url(url: str) -> bool:
    """Validates that a URL is non-empty, uses http/https, and does not target private networks."""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False
        if hostname in BLOCKED_HOSTNAMES:
            return False
        if any(hostname.startswith(prefix) for prefix in PRIVATE_IP_PREFIXES):
            return False
        return True
    except Exception:
        return False


def convert_json_schema_to_gemini(schema: Any) -> Any:
    """
    Recursively converts standard JSON Schema into a schema dict
    strictly compatible with Gemini types.FunctionDeclaration / types.Schema.
    - Capitalizes type names (string -> STRING, object -> OBJECT, etc.)
    - Removes unsupported JSON-schema metas ($schema, additionalProperties)
    """
    if not isinstance(schema, dict):
        return schema

    cleaned: Dict[str, Any] = {}
    for key, value in schema.items():
        if key in ("$schema", "additionalProperties", "$id", "title"):
            continue

        if key == "type" and isinstance(value, str):
            cleaned[key] = value.upper()
        elif key == "properties" and isinstance(value, dict):
            cleaned[key] = {
                prop_name: convert_json_schema_to_gemini(prop_val)
                for prop_name, prop_val in value.items()
            }
        elif key == "items" and isinstance(value, dict):
            cleaned[key] = convert_json_schema_to_gemini(value)
        elif key == "required" and isinstance(value, list):
            cleaned[key] = [str(r) for r in value]
        else:
            cleaned[key] = value

    if "type" not in cleaned:
        cleaned["type"] = "OBJECT"

    return cleaned


class MCPClientService:
    """
    Client service managing connections, tool discovery, and execution
    with Model Context Protocol (MCP) servers using official Python MCP SDK.
    """

    def __init__(self):
        self.timeout_seconds = settings.MCP_TIMEOUT_SECONDS
        self.max_tool_calls = settings.MCP_MAX_TOOL_CALLS

    @property
    def is_enabled(self) -> bool:
        return settings.is_mcp_configured()

    @property
    def allowed_tools(self) -> Set[str]:
        return settings.mcp_allowed_tools_set

    def _get_server_params(self) -> StdioServerParameters:
        """Constructs StdioServerParameters from app configuration."""
        import os
        env = os.environ.copy()
        env.update(settings.mcp_env_dict)
        return StdioServerParameters(
            command=settings.MCP_SERVER_COMMAND,
            args=settings.mcp_args_list,
            env=env,
        )

    async def _create_session_context(self):
        """Asynchronous context generator yielding (read_stream, write_stream)."""
        if settings.MCP_TRANSPORT == "sse":
            if not settings.MCP_SERVER_URL:
                raise ValueError("MCP_SERVER_URL must be configured when MCP_TRANSPORT is 'sse'")
            return sse_client(settings.MCP_SERVER_URL)
        else:
            params = self._get_server_params()
            return stdio_client(params)

    async def test_connection(self) -> Dict[str, Any]:
        """Tests connection to MCP server and returns discovery diagnostics."""
        if not self.is_enabled:
            return {
                "enabled": False,
                "connected": False,
                "message": "MCP is disabled in configuration (MCP_ENABLED=false).",
                "tools": [],
            }

        try:
            tools = await self.discover_tools()
            return {
                "enabled": True,
                "connected": True,
                "transport": settings.MCP_TRANSPORT,
                "server_command": settings.MCP_SERVER_COMMAND,
                "allowed_tools": list(self.allowed_tools),
                "discovered_tools_count": len(tools),
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "is_allowed": t.name in self.allowed_tools,
                    }
                    for t in tools
                ],
            }
        except Exception as e:
            logger.warning(f"MCP server health test failed: {e}")
            return {
                "enabled": True,
                "connected": False,
                "transport": settings.MCP_TRANSPORT,
                "server_command": settings.MCP_SERVER_COMMAND,
                "error": str(e),
                "tools": [],
            }

    async def discover_tools(self) -> List[Any]:
        """Discovers available tools exposed by the configured MCP server."""
        if not self.is_enabled:
            return []

        async def _run_discovery():
            client_ctx = await self._create_session_context()
            async with client_ctx as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return result.tools

        try:
            return await asyncio.wait_for(_run_discovery(), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(f"MCP tool discovery timed out after {self.timeout_seconds}s")
            raise TimeoutError(f"MCP server discovery timed out after {self.timeout_seconds} seconds")
        except Exception as e:
            logger.error(f"Failed to discover MCP tools: {e}")
            raise

    async def get_gemini_tools(self) -> Tuple[List[types.Tool], Dict[str, Any]]:
        """
        Retrieves discovered MCP tools converted to Gemini function declarations,
        filtered strictly by allowed tools allowlist.
        Returns: (gemini_tools, tool_catalog_by_name)
        """
        if not self.is_enabled:
            return [], {}

        try:
            raw_tools = await self.discover_tools()
        except Exception as e:
            logger.warning(f"Could not load MCP tools for Gemini: {e}")
            return [], {}

        function_declarations: List[types.FunctionDeclaration] = []
        catalog: Dict[str, Any] = {}

        for t in raw_tools:
            tool_name = getattr(t, "name", "")
            if not tool_name or tool_name not in self.allowed_tools:
                logger.debug(f"Skipping unallowed or unnamed MCP tool: {tool_name}")
                continue

            raw_schema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", {})
            if hasattr(raw_schema, "model_dump"):
                raw_schema = raw_schema.model_dump()

            converted_schema = convert_json_schema_to_gemini(raw_schema)
            description = getattr(t, "description", "") or f"External research tool {tool_name}"

            fd = types.FunctionDeclaration(
                name=tool_name,
                description=description,
                parameters=converted_schema,
            )
            function_declarations.append(fd)
            catalog[tool_name] = {
                "name": tool_name,
                "description": description,
                "raw_schema": raw_schema,
                "tool_obj": t,
            }

        if not function_declarations:
            return [], {}

        gemini_tool = types.Tool(function_declarations=function_declarations)
        return [gemini_tool], catalog

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_catalog: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a named MCP tool with strict validation:
        1. Tool is in approved allowlist
        2. Arguments validate against discovered JSON schema
        3. SSRF validation on any URL arguments
        4. Invocation timeout protection
        5. Content size truncation
        """
        # 1. Allowlist enforcement
        if tool_name not in self.allowed_tools:
            raise PermissionError(f"Tool '{tool_name}' is not in the approved MCP tools allowlist.")

        # 2. Schema validation
        schema = None
        if tool_catalog and tool_name in tool_catalog:
            schema = tool_catalog[tool_name].get("raw_schema")

        if schema:
            try:
                jsonschema.validate(instance=arguments, schema=schema)
            except jsonschema.ValidationError as ve:
                raise ValueError(f"Invalid arguments for tool '{tool_name}': {ve.message}")

        # 3. SSRF validation if URL parameter is present
        for key in ("url", "uri", "link", "target_url"):
            if key in arguments and isinstance(arguments[key], str):
                if not is_safe_url(arguments[key]):
                    raise ValueError(f"Unsafe or internal URL rejected for parameter '{key}': {arguments[key]}")

        # 4. Execute via MCP session
        async def _run_call():
            client_ctx = await self._create_session_context()
            async with client_ctx as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    res = await session.call_tool(tool_name, arguments)
                    return res

        try:
            res = await asyncio.wait_for(_run_call(), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(f"MCP tool '{tool_name}' call timed out after {self.timeout_seconds}s")
            return {
                "error": f"Tool '{tool_name}' timed out after {self.timeout_seconds} seconds.",
                "is_error": True,
                "content": "",
            }
        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' execution error: {e}")
            return {
                "error": f"Tool '{tool_name}' execution error: {str(e)}",
                "is_error": True,
                "content": "",
            }

        # 5. Extract and sanitize output
        is_error = getattr(res, "is_error", False)
        content_items = getattr(res, "content", []) or []

        text_parts = []
        for c in content_items:
            t = getattr(c, "text", "")
            if t:
                text_parts.append(t)

        raw_text = "\n".join(text_parts) if text_parts else str(res)
        # Truncate content to safe size limit (20KB) to prevent prompt explosion
        if len(raw_text) > 20000:
            raw_text = raw_text[:20000] + "\n...[Output truncated for size safety]"

        return {
            "tool_name": tool_name,
            "is_error": is_error,
            "content": raw_text,
        }

    @staticmethod
    def parse_sources_from_tool_output(
        tool_name: str,
        tool_output: str,
    ) -> List[ExternalSource]:
        """
        Parses structured sources (title, url, snippet, date) from search outputs.
        Supports JSON arrays, Brave Search outputs, and Markdown links.
        Guarantees that invented or malformed URLs are dropped.
        """
        sources: List[ExternalSource] = []
        if not tool_output or not tool_output.strip():
            return sources

        # Attempt JSON parse first
        try:
            data = json.loads(tool_output)
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Common search response shapes
                for key in ("results", "web", "organic", "items", "web_results"):
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                if not items and "results" in data.get("web", {}):
                    items = data["web"]["results"]

            for it in items:
                if isinstance(it, dict):
                    title = it.get("title") or it.get("name") or "External Legal Document"
                    url = it.get("url") or it.get("link") or ""
                    snippet = it.get("description") or it.get("snippet") or it.get("text") or ""
                    date = it.get("page_age") or it.get("date") or it.get("published_date") or None

                    if url and is_safe_url(url):
                        sources.append(
                            ExternalSource(
                                title=str(title).strip(),
                                url=str(url).strip(),
                                snippet=str(snippet)[:300].strip() if snippet else None,
                                publication_date=str(date).strip() if date else None,
                                source_type=MCPClientService._categorize_source(url, str(title)),
                                verified=True,
                            )
                        )
            if sources:
                return sources[:8]
        except Exception:
            pass

        # Fallback: Extract Markdown links [Title](URL) or direct URLs
        md_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)")
        for match in md_pattern.finditer(tool_output):
            title, url = match.group(1).strip(), match.group(2).strip()
            if is_safe_url(url):
                # Extract surrounding sentence as snippet if possible
                start = max(0, match.start() - 100)
                end = min(len(tool_output), match.end() + 150)
                snippet_candidate = tool_output[start:end].replace(match.group(0), "").strip()
                sources.append(
                    ExternalSource(
                        title=title or "Legal Reference",
                        url=url,
                        snippet=snippet_candidate[:250] if snippet_candidate else None,
                        source_type=MCPClientService._categorize_source(url, title),
                        verified=True,
                    )
                )

        # Deduplicate sources by URL
        unique_sources: List[ExternalSource] = []
        seen_urls = set()
        for s in sources:
            if s.url not in seen_urls:
                seen_urls.add(s.url)
                unique_sources.append(s)

        return unique_sources[:8]

    @staticmethod
    def _categorize_source(url: str, title: str) -> str:
        """Categorizes legal sources into verifiable types."""
        combined = (url + " " + title).lower()
        if any(w in combined for w in ("judgments", "supremecourt", "indiankanoon", "court", "tribunal", "case", "v.", "vs")):
            return "Judiciary / Court Decision"
        if any(w in combined for w in ("act", "statute", "section", "legislat", "bareact", "gazette", "gov.in", ".gov")):
            return "Statute / Official Government"
        if any(w in combined for w in ("law", "barandbench", "livelaw", "mondaq", "lexology", "legal")):
            return "Legal Commentary & Analysis"
        return "Web Resource"


mcp_service = MCPClientService()
