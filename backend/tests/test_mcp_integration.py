import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models.schemas import (
    CitationSource,
    EvidenceStatus,
    ExternalSearchStatus,
    ResearchMode,
)
from app.services.llm_service import GeminiLLMService
from app.services.mcp_service import (
    MCPClientService,
    convert_json_schema_to_gemini,
    is_safe_url,
)


def create_dummy_citation(chunk_id: str, text: str, section: str = "General", page: int = 1):
    return CitationSource(
        chunk_id=chunk_id,
        document_id="contract_emp_1",
        filename="Employment_Bond_Agreement.pdf",
        chunk_index=0,
        section_title=section,
        page_number=page,
        snippet=text,
        similarity_score=0.91,
        verified=True,
    )


class TestMCPIntegration:
    """Tests for Model Context Protocol client, schema validation, SSRF checks, and research workflows."""

    def test_ssrf_url_validation(self):
        """Validates that unsafe internal, loopback, or private network URLs are strictly rejected."""
        # Unsafe URLs
        assert is_safe_url("http://localhost:8080/secret") is False
        assert is_safe_url("http://127.0.0.1:5000/internal") is False
        assert is_safe_url("http://192.168.1.1/admin") is False
        assert is_safe_url("http://10.0.0.1/metadata") is False
        assert is_safe_url("http://172.16.0.1/private") is False
        assert is_safe_url("ftp://example.com/file") is False
        assert is_safe_url("file:///etc/passwd") is False
        assert is_safe_url("") is False

        # Safe public URLs
        assert is_safe_url("https://indiankanoon.org/doc/1431519/") is True
        assert is_safe_url("https://delcode.delaware.gov/title8/index.html") is True
        assert is_safe_url("http://legalserviceindia.com/article.htm") is True

    def test_schema_conversion_for_gemini(self):
        """Verifies conversion of standard MCP JSON schema to Gemini-compatible upper-cased types."""
        mcp_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Legal research search query",
                },
                "count": {
                    "type": "integer",
                    "description": "Max results to return",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        }

        converted = convert_json_schema_to_gemini(mcp_schema)
        assert "$schema" not in converted
        assert "additionalProperties" not in converted
        assert converted["type"] == "OBJECT"
        assert converted["properties"]["query"]["type"] == "STRING"
        assert converted["properties"]["count"]["type"] == "INTEGER"
        assert converted["required"] == ["query"]

    @pytest.mark.asyncio
    async def test_tool_allowlist_enforcement(self):
        """Disallowed tools must raise PermissionError and never be executed."""
        mcp = MCPClientService()
        # Attempt calling a tool not in the allowlist
        with pytest.raises(PermissionError) as exc_info:
            await mcp.execute_tool("arbitrary_bash_command", {"command": "rm -rf /"})
        assert "not in the approved MCP tools allowlist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tool_argument_validation(self):
        """Tool arguments failing JSON Schema validation must be rejected with ValueError."""
        mcp = MCPClientService()
        tool_catalog = {
            "brave_web_search": {
                "raw_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                }
            }
        }

        # Missing required parameter 'query'
        with pytest.raises(ValueError) as exc_info:
            await mcp.execute_tool("brave_web_search", {"invalid_param": 123}, tool_catalog=tool_catalog)
        assert "Invalid arguments for tool" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ssrf_argument_rejection(self):
        """Any URL arguments resolving to internal or private networks must be blocked."""
        mcp = MCPClientService()
        with pytest.raises(ValueError) as exc_info:
            await mcp.execute_tool("fetch", {"url": "http://127.0.0.1:8000/internal"})
        assert "Unsafe or internal URL rejected" in str(exc_info.value)

    def test_parse_sources_from_tool_output(self):
        """Parses structured source metadata from various MCP search output shapes."""
        mcp = MCPClientService()

        # 1. JSON output shape (common in Brave search)
        json_search_output = json.dumps({
            "results": [
                {
                    "title": "Section 27 in The Indian Contract Act, 1872",
                    "url": "https://indiankanoon.org/doc/1431519/",
                    "description": "Agreement in restraint of trade, void. Every agreement by which anyone is restrained from exercising a lawful profession is void.",
                    "page_age": "2024-01-15",
                },
                {
                    "title": "Supreme Court on Enforceability of Employment Bonds in India",
                    "url": "https://livelaw.in/top-stories/employment-bond-validity-supreme-court-23456",
                    "description": "The court held that unreasonable penalty amounts without actual training expenses cannot be recovered.",
                },
                {
                    "title": "Internal Admin Page",
                    "url": "http://localhost:8000/admin",  # Must be filtered out
                    "description": "Secret internal page",
                },
            ]
        })

        sources = mcp.parse_sources_from_tool_output("brave_web_search", json_search_output)
        assert len(sources) == 2
        assert sources[0].title == "Section 27 in The Indian Contract Act, 1872"
        assert sources[0].url == "https://indiankanoon.org/doc/1431519/"
        assert sources[0].publication_date == "2024-01-15"
        assert sources[0].source_type == "Statute / Official Government" or "Judiciary" in sources[0].source_type

        assert sources[1].title == "Supreme Court on Enforceability of Employment Bonds in India"
        assert sources[1].url == "https://livelaw.in/top-stories/employment-bond-validity-supreme-court-23456"
        # The localhost url must not be included
        assert not any("localhost" in s.url for s in sources)

        # 2. Markdown output shape
        markdown_search_output = (
            "Found legal precedents:\n"
            "- [Niranjan Shankar Golikari v. Century Spg. & Mfg. Co.](https://indiankanoon.org/doc/238478/): Negative covenants during employment term.\n"
            "- [Superintendence Company Of India v. Krishan Murgai](https://indiankanoon.org/doc/928374/): Post-service restrictions void under Section 27."
        )
        md_sources = mcp.parse_sources_from_tool_output("web_search", markdown_search_output)
        assert len(md_sources) == 2
        assert md_sources[0].url == "https://indiankanoon.org/doc/238478/"
        assert "Niranjan Shankar" in md_sources[0].title


class TestLegalResearchWorkflow:
    """Tests the full RAG + MCP External Legal Research pipeline with Gemini."""

    @pytest.fixture
    def mock_gemini_service(self):
        with patch("app.services.llm_service.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            service = GeminiLLMService(api_key="mock_key")
            service._client = mock_client
            yield service, mock_client

    @pytest.mark.asyncio
    async def test_document_only_mode_ignores_mcp(self, mock_gemini_service):
        """In document_only mode, MCP search is never invoked even if enabled."""
        service, mock_client = mock_gemini_service
        mock_mcp = MagicMock(spec=MCPClientService)
        mock_mcp.is_enabled = True

        citations = [
            create_dummy_citation("c_bond", "Employee agrees to serve for 36 months or pay ₹200,000 as liquidated damages.")
        ]

        llm_payload = {
            "answer": "The agreement contains an employment service bond requiring ₹200,000 payment for early resignation.",
            "contract_findings": "Section 5 requires ₹200,000 for departure before 36 months.",
            "external_findings": None,
            "legal_implications": "Clause imposes a financial exit barrier.",
            "uncertainties_and_advice": "Consult counsel.",
            "evidence_status": "SUFFICIENT",
            "conflicting_clauses": [],
            "limitations": [],
            "citations": [{"chunk_id": "c_bond", "quote": "₹200,000", "reason": "Mentions bond amount"}],
        }
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(llm_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = await service.answer_contract_question_async(
            contract_id="contract_emp_1",
            query="Is this ₹2 lakh employment bond enforceable in India?",
            retrieved_citations=citations,
            research_mode=ResearchMode.DOCUMENT_ONLY,
            mcp_svc=mock_mcp,
        )

        # MCP search must NOT be invoked in document_only mode
        mock_mcp.execute_tool.assert_not_called()
        assert response.research_mode == ResearchMode.DOCUMENT_ONLY
        assert response.external_research_used is False
        assert response.external_search_status == ExternalSearchStatus.NOT_REQUESTED
        assert len(response.external_sources) == 0
        assert len(response.citations) == 1
        assert response.citations[0].chunk_id == "c_bond"

    @pytest.mark.asyncio
    async def test_external_research_mode_with_mcp(self, mock_gemini_service):
        """In external_research mode, executes MCP search and integrates legal authorities."""
        service, mock_client = mock_gemini_service

        mock_mcp = AsyncMock(spec=MCPClientService)
        mock_mcp.is_enabled = True
        mock_mcp.allowed_tools = {"brave_web_search", "web_search"}
        dummy_tool = MagicMock()
        dummy_tool.name = "brave_web_search"
        mock_mcp.discover_tools.return_value = [dummy_tool]

        mock_mcp.execute_tool.return_value = {
            "tool_name": "brave_web_search",
            "is_error": False,
            "content": json.dumps({
                "results": [
                    {
                        "title": "Section 27 Indian Contract Act - Restraint of Trade",
                        "url": "https://indiankanoon.org/doc/1431519/",
                        "description": "Agreements in restraint of trade are void. Indian courts require proof of actual training expenses incurred by the employer.",
                    }
                ]
            }),
        }

        mock_mcp.parse_sources_from_tool_output = MCPClientService.parse_sources_from_tool_output

        citations = [
            create_dummy_citation("c_bond_1", "Employee shall pay ₹200,000 if terminating within 36 months.")
        ]

        llm_payload = {
            "answer": "Under Indian law, employment bonds are not automatically enforceable for the full penalty amount.",
            "contract_findings": "Clause 8 specifies a ₹2,00,000 exit penalty for departure within 3 years.",
            "external_findings": "Section 27 of the Indian Contract Act void restrictions in restraint of trade. Under Section 74, courts only award reasonable compensation for actual training expenses incurred.",
            "legal_implications": "The employer cannot recover ₹2,00,000 unless they prove equivalent actual investment in specialized training.",
            "uncertainties_and_advice": "Enforceability depends on employer's ability to demonstrate specific training receipts in court. Not binding legal advice.",
            "evidence_status": "SUFFICIENT",
            "conflicting_clauses": [],
            "limitations": [],
            "citations": [{"chunk_id": "c_bond_1", "quote": "₹200,000", "reason": "Bond penalty clause"}],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(llm_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = await service.answer_contract_question_async(
            contract_id="contract_emp_1",
            query="Is this ₹2 lakh employment bond enforceable in India?",
            retrieved_citations=citations,
            research_mode=ResearchMode.EXTERNAL_RESEARCH,
            mcp_svc=mock_mcp,
        )

        assert response.external_research_used is True
        assert response.external_search_status == ExternalSearchStatus.SUCCESS
        assert len(response.external_sources) == 1
        assert response.external_sources[0].url == "https://indiankanoon.org/doc/1431519/"
        assert response.contract_findings is not None
        assert response.external_findings is not None
        assert response.legal_implications is not None
        assert response.uncertainties_and_advice is not None
        assert len(response.citations) == 1
        assert response.citations[0].chunk_id == "c_bond_1"

    @pytest.mark.asyncio
    async def test_mcp_server_unavailable_graceful_degradation(self, mock_gemini_service):
        """When MCP server is down or unreachable, service notes unavailability and grounds response on contract."""
        service, mock_client = mock_gemini_service

        mock_mcp = AsyncMock(spec=MCPClientService)
        mock_mcp.is_enabled = True
        mock_mcp.discover_tools.side_effect = TimeoutError("MCP server timed out")

        citations = [
            create_dummy_citation("c_noncompete", "Employee shall not work for any competitor globally for 5 years.")
        ]

        llm_payload = {
            "answer": "The contract contains a 5-year global non-compete clause.",
            "contract_findings": "Article 5 prohibits employment with any competitor globally for 5 years post-termination.",
            "external_findings": "External legal research via MCP is currently unavailable.",
            "legal_implications": "Clause imposes broad competitive restrictions.",
            "uncertainties_and_advice": "Consult a legal practitioner regarding non-compete enforceability in your jurisdiction.",
            "evidence_status": "PARTIAL",
            "conflicting_clauses": [],
            "limitations": ["Live external legal research via MCP was unavailable."],
            "citations": [{"chunk_id": "c_noncompete", "quote": "5 years", "reason": "Non-compete term"}],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(llm_payload)
        mock_client.models.generate_content.return_value = mock_resp

        response = await service.answer_contract_question_async(
            contract_id="contract_emp_1",
            query="Is a 5-year global non-compete enforceable?",
            retrieved_citations=citations,
            research_mode=ResearchMode.EXTERNAL_RESEARCH,
            mcp_svc=mock_mcp,
        )

        # External research should be reported as unavailable
        assert response.external_research_used is False
        assert response.external_search_status == ExternalSearchStatus.UNAVAILABLE
        assert len(response.external_sources) == 0
        assert len(response.citations) == 1
        assert response.citations[0].chunk_id == "c_noncompete"

    @pytest.mark.asyncio
    async def test_auto_mode_detects_legal_inquiry(self, mock_gemini_service):
        """In AUTO mode, enforceability queries trigger external research while pure contract lookups do not."""
        service, _ = mock_gemini_service

        assert service._should_trigger_external_research(
            "Is this ₹2 lakh employment bond enforceable in India?",
            ResearchMode.AUTO,
        ) is True

        assert service._should_trigger_external_research(
            "Is the 5-year non-compete clause void under Section 27 of the Indian Contract Act?",
            ResearchMode.AUTO,
        ) is True

        assert service._should_trigger_external_research(
            "What is the notice period for contract termination in Section 4?",
            ResearchMode.AUTO,
        ) is False

        assert service._should_trigger_external_research(
            "How many days does the customer have to pay invoices?",
            ResearchMode.AUTO,
        ) is False
