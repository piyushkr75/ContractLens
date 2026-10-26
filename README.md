# ContractLens — AI-Powered Contract Risk Intelligence Platform

<div align="center">

**Enterprise-grade contract analysis using Google Gemini AI, FAISS in-memory vector search, and React.**

*Identify hidden liabilities • Flag asymmetric indemnities • Auto-generate clause counter-proposals*

</div>

---

## 🏗 Architecture Overview

ContractLens is a full-stack application with a **zero-database architecture**. All document chunks, embeddings, FAISS indexes, risk analyses, and conversation state live entirely in memory.

```
┌────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite + Tailwind)      │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐  │
│  │  Upload   │ │ Risk Overview │ │ RAG Chat │ │ Export Report │  │
│  │  Panel    │ │ & Clause Audit│ │ (FAISS)  │ │ (TXT/JSON)   │  │
│  └─────┬────┘ └──────┬───────┘ └────┬─────┘ └──────┬───────┘  │
│        └──────────────┴──────────────┴──────────────┘          │
│                         Vite Proxy → :8000                     │
└────────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI + Python)                │
│                                                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │ Document Ingest  │  │ Gemini Embeddings│  │ Gemini LLM    │  │
│  │ PyMuPDF/docx     │  │ text-embedding-  │  │ gemini-2.0-   │  │
│  │ + chunking       │  │ 004 (768-dim)    │  │ flash         │  │
│  └────────┬────────┘  └────────┬────────┘  └──────┬────────┘  │
│           │                    │                    │           │
│  ┌────────┴────────────────────┴────────────────────┴────────┐ │
│  │              In-Memory State Store (Python dicts)          │ │
│  │  contracts{}  chunks{}  analyses{}  chat_histories{}       │ │
│  └────────────────────────────┬───────────────────────────────┘ │
│                               │                                │
│  ┌────────────────────────────┴───────────────────────────────┐ │
│  │              FAISS IndexFlatIP (Cosine Similarity)          │ │
│  │         Per-contract in-memory vector indexes               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                │
│  📁 uploads/ — Local file storage only (no cloud/DB)           │
└────────────────────────────────────────────────────────────────┘
```

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Document Ingestion** | Upload PDF (PyMuPDF) or DOCX (python-docx) contracts with magic-byte validation, safe filenames, and path traversal protection |
| **Section-Aware Chunking** | Overlapping chunks that preserve page numbers and section headings |
| **Gemini Embeddings** | `text-embedding-004` via official Google Gen AI SDK with batching and rate-limit retries |
| **FAISS Vector Search** | In-memory `IndexFlatIP` with cosine similarity, per-document filtering, and configurable top-k |
| **Risk Analysis** | Deep clause-by-clause legal risk audit with category breakdowns and mitigation recommendations |
| **RAG Q&A** | Conversational question answering grounded in FAISS-retrieved evidence with verified citations |
| **Citation Verification** | Every citation ID from the LLM is validated against real chunk metadata — fabricated IDs are discarded |
| **Prompt Injection Defense** | Contract text wrapped in `<UNTRUSTED_CONTRACT_TEXT>` tags with explicit injection defense instructions |
| **Export Reports** | Download risk intelligence reports in TXT or JSON format |
| **Heuristic Fallback** | Full functionality without an API key using deterministic legal heuristic analysis |

## 📁 Project Structure

```
Contract Risk Intelligence/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app, lifespan, CORS, routers
│   │   ├── config.py                  # Pydantic Settings (env vars)
│   │   ├── api/
│   │   │   ├── deps.py                # Dependency injection
│   │   │   └── routes/
│   │   │       ├── health.py          # GET /api/health
│   │   │       ├── contracts.py       # POST upload, GET list, GET detail, DELETE
│   │   │       ├── analysis.py        # POST analyze, GET analysis, compare contracts
│   │   │       ├── chat.py            # POST chat, GET history
│   │   │       └── mcp_routes.py      # GET /api/mcp/status, POST /api/mcp/query
│   │   ├── core/
│   │   │   └── memory_store.py        # Thread-safe in-memory state (singleton)
│   │   ├── models/
│   │   │   └── schemas.py             # Pydantic models (risk, chat, citations, comparison)
│   │   └── services/
│   │       ├── document_processor.py  # PyMuPDF + python-docx text extraction & chunking
│   │       ├── embedding_service.py   # Google Gemini embeddings with fallback
│   │       ├── vector_store.py        # FAISS IndexFlatIP wrapper
│   │       ├── llm_service.py         # Gemini LLM for analysis, comparison & RAG Q&A
│   │       └── mcp_service.py         # MCP external legal research tool integration
│   ├── tests/
│   │   ├── test_document_ingestion.py
│   │   ├── test_embedding_service.py
│   │   ├── test_vector_store.py
│   │   ├── test_question_answering.py
│   │   ├── test_risk_analysis.py
│   │   ├── test_contract_comparison.py
│   │   ├── test_mcp_integration.py
│   │   ├── test_eval_suite.py
│   │   └── eval/
│   │       ├── synthetic_contracts.py # 5 synthetic contracts across diverse domains
│   │       ├── gold_test_cases.py     # 40 gold evaluation queries & expected answers
│   │       ├── eval_harness.py        # Automated benchmark runner & metrics calculator
│   │       └── EVALUATION_REPORT.md   # Empirical evaluation report with token & cost analysis
│   ├── uploads/                       # Local file storage (gitignored)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Main application with tab routing
│   │   ├── main.jsx                   # React entry point
│   │   ├── index.css                  # Tailwind + glassmorphism + animations
│   │   ├── components/
│   │   │   ├── Navbar.jsx             # Top bar with health indicators
│   │   │   ├── FileUpload.jsx         # Drag-and-drop upload + sample contract
│   │   │   ├── RiskOverview.jsx       # Risk gauge, executive summary, red flags
│   │   │   ├── ClauseInspector.jsx    # Clause cards with redline suggestions
│   │   │   ├── ContractChat.jsx       # RAG chat with FAISS citations
│   │   │   ├── DocumentViewer.jsx     # Raw text + chunk explorer with search
│   │   │   ├── RiskReport.jsx         # Exportable risk report (TXT/JSON)
│   │   │   └── HealthModal.jsx        # System health inspection modal
│   │   └── services/
│   │       └── api.js                 # API client + sample contract text
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
├── .gitignore
├── .env.example
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Google Gemini API Key** (free tier available at [aistudio.google.com](https://aistudio.google.com/app/apikey))

### 1. Clone & Configure

```bash
cd "Contract Risk Intelligence"

# Create backend .env from template
cp backend/.env.example backend/.env
# Edit backend/.env and add your Gemini API key:
#   GEMINI_API_KEY=your_actual_api_key_here
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000` with interactive docs at `/docs`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the Vite dev server
npm run dev
```

The frontend will be available at `http://localhost:5173` with automatic proxy to the backend.

### 4. Test (Optional)

```bash
cd backend
python -m pytest tests/ -v
```

## 🔧 Configuration

All configuration is via environment variables in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google Gemini API key (required for AI features) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model for analysis and Q&A |
| `GEMINI_EMBEDDING_MODEL` | `text-embedding-004` | Embedding model name |
| `GEMINI_EMBEDDING_DIMENSION` | `768` | Vector dimension for FAISS |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between adjacent chunks |
| `MAX_FILE_SIZE_MB` | `25` | Maximum upload file size |
| `UPLOAD_DIR` | `./uploads` | Local file storage directory |
| `CORS_ORIGINS` | `localhost:5173` | Allowed frontend origins |

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | System health with FAISS, Gemini, and MCP status |
| `POST` | `/api/contracts/upload` | Upload PDF/DOCX, validate magic bytes, chunk, embed, and index in FAISS |
| `GET` | `/api/contracts` | List all in-memory contracts with risk overview |
| `GET` | `/api/contracts/{id}` | Get contract detail, metadata, and raw text preview |
| `GET` | `/api/contracts/{id}/chunks` | Get all indexed chunks with page numbers, section headers, and chunk IDs |
| `GET` | `/api/contracts/{id}/download` | Stream uploaded contract file for browser preview |
| `DELETE` | `/api/contracts/{id}` | Delete contract, release local file, and clear in-memory FAISS index |
| `POST` | `/api/contracts/{id}/analyze` | Run Gemini legal risk intelligence analysis |
| `GET` | `/api/contracts/{id}/analysis` | Get cached analysis (auto-triggers if not yet analyzed) |
| `POST` | `/api/contracts/compare` | Compare two contracts side-by-side with verified citations |
| `POST` | `/api/contracts/{id}/chat` | RAG Q&A with FAISS retrieval, verified citations, and MCP external research |
| `GET` | `/api/contracts/{id}/chat/history` | Get in-memory conversation thread history |
| `GET` | `/api/mcp/status` | MCP server connection diagnostics and discovered tools |

## 📊 Reproducible Evaluation Suite & Benchmark

ContractLens includes an enterprise-grade evaluation suite with **zero database dependencies** to benchmark retrieval and answer quality across **5 synthetic contracts** and **40 manually verified gold test cases**:

```bash
cd backend

# Run the complete evaluation harness (evaluates vector-only vs improved retrieval)
python -m tests.eval.eval_harness

# Run with live Gemini API generation (requires billing API key)
python -m tests.eval.eval_harness --use-llm

# Run dedicated deterministic unit tests (24 tests)
python -m pytest tests/test_eval_suite.py -v
```

### Empirical Measured Results (from `eval_results/`)

| Metric | Vector-Only Baseline | Improved Hybrid Config | Impact / Relative Gain |
| :--- | :---: | :---: | :--- |
| **MRR@5 (Targeted Clauses)** | **0.4357** | **0.4762** | **+9.3% relative improvement** |
| **MRR@5 (Overall)** | **0.6050** | **0.6333** | **+4.7% relative improvement** |
| **Payment Clause MRR@5** | 0.1000 | **0.2857** | **+185.7% relative improvement** |
| **Indemnity Clause MRR@5** | 0.6806 | **0.8056** | **+18.4% relative improvement** |
| **Liability Clause MRR@5** | 0.8056 | **0.8889** | **+10.3% relative improvement** |
| **Citation Validity** | **1.0000 (100%)** | **1.0000 (100%)** | Zero hallucinated citations |
| **Answer Faithfulness** | **0.7808 (78.1%)** | **0.7808 (78.1%)** | High keyword precision |
| **Abstention Accuracy** | **1.0000 (100%)** | **1.0000 (100%)** | Perfect abstention on missing/unsupported |
| **Conflict Detection Accuracy**| **0.8750 (87.5%)** | **0.8750 (87.5%)** | Accurately isolates contradictory clauses |
| **Risk Finding Accuracy** | **0.8333 (83.3%)** | **0.8333 (83.3%)** | Calibrated across 12 risk cases |
| **Retrieval Latency** | **0.36 ms** | **0.71 ms** | Ultra-fast in-memory processing |
| **Total Prompt Tokens** | 14,713 | **13,158** | **-1,555 prompt tokens saved (-10.6%)** |
| **Measured API Cost** | $0.003679 | **$0.003495** | **$0.000087 per query** ($< 0.01$¢) |

*Full evaluation report, category score breakdowns, and methodology formulas are documented in [`backend/tests/eval/EVALUATION_REPORT.md`](file:///c:/Users/Ayushsingh/Desktop/PIYUSHHHHHHH/react_projects/Contract%20Risk%20Intelligence/backend/tests/eval/EVALUATION_REPORT.md).*

## 🔒 Security Features

- **Safe filenames**: All uploaded filenames are sanitized via `sanitize_filename` (regex stripping path separators and null bytes) to prevent directory traversal
- **Path traversal protection**: File paths are strictly resolved and validated against the upload directory with `resolve_safe_path`
- **Magic byte validation**: File content headers are checked against claimed file type (`%PDF-` for PDF, `PK\x03\x04` with zip structure check for DOCX)
- **Prompt injection defense**: Contract text and external legal citations are encapsulated inside XML delimiters (`<UNTRUSTED_CONTRACT_TEXT>`, `<UNTRUSTED_CONTRACT_EVIDENCE>`, `<UNTRUSTED_EXTERNAL_RESEARCH>`) with explicit instructions directing the model to ignore user-injected instructions
- **Citation verification**: LLM-generated citation chunk IDs are verified against actual retrieved evidence chunks in `evidence_map`; ungrounded/fabricated IDs are automatically logged, stripped, and reported in `limitations`
- **SSRF protection**: MCP outbound requests enforce strict private network address validation, blocking `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and `169.254.0.0/16`
- **Memory-safe isolated sessions**: Zero database or persistent vector DB leakage; thread-safe lock-protected in-memory store
- **Temporary file cleanup**: Uploaded files undergo safe garbage collection and unlinking on deletion
- **Rate limiting & API backoff**: Client-side exponential backoff retry for Gemini API rate limits (HTTP 429/503); application-level rate limiting (e.g., via Nginx reverse proxy or SlowAPI middleware) is recommended for public multi-tenant deployments
- **No public file serving**: Uploaded files are stored in the server's local directory and accessed only via validated backend endpoints

## 🧪 Testing

The comprehensive test suite contains **85 deterministic unit and integration tests** across 8 test suites:

- **Document Ingestion (`test_document_ingestion.py`)**: PDF/DOCX parsing, section-aware chunking, page metadata preservation, corrupted file handling, empty document detection, scanned PDF handling
- **Embedding Service (`test_embedding_service.py`)**: Batch embedding, fallback deterministic vectors, L2 normalization, rate-limit retry logic with exponential backoff
- **Vector Store (`test_vector_store.py`)**: FAISS index operations, per-document filtering, similarity threshold, cosine similarity correctness
- **Question Answering (`test_question_answering.py`)**: Fabricated citation rejection, missing evidence handling, conflicting evidence detection, prompt injection resilience
- **Risk Analysis (`test_risk_analysis.py`)**: Severity categorization, clause classification, red flag detection, recommendation formatting
- **Contract Comparison (`test_contract_comparison.py`)**: Dual-contract alignment, clause diffing, risk divergence scoring
- **MCP Integration (`test_mcp_integration.py`)**: Model Context Protocol discovery, tool execution, SSRF validation, graceful offline fallback
- **Evaluation Suite (`test_eval_suite.py`)**: Verification of 40 gold test cases, metrics calculation (Recall@5, MRR@5, Faithfulness, Abstention, Conflict Detection), benchmark reproducibility

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

## 🚀 Production Deployment

### 1. In-Memory Concurrency Considerations

ContractLens is designed around a zero-database, in-memory FAISS vector store. Because vector indexes and session state reside in Python process memory:

- **Recommended Worker Model**: Deploy with a single Uvicorn process or use sticky sessions (session affinity) on your load balancer.
- **Worker Command**:
  ```bash
  # Single worker (preserves state across all concurrent requests)
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
  ```
- **State Lifecycle**: Server restarts clear in-memory vector indices and analyses. Uploaded files remain in `uploads/` unless deleted via the API.

### 2. Frontend Production Build

Build the optimized React bundle using Vite:

```bash
cd frontend
npm run build
# Output assets are generated in frontend/dist/
```

### 3. Nginx Reverse Proxy & Rate Limiting

Deploy behind Nginx to serve the static frontend, proxy API requests to FastAPI, and enforce IP-based rate limiting:

```nginx
# Define rate limiting zone
limit_req_zone $binary_remote_addr zone=contractlens_limit:10m rate=10r/s;

server {
    listen 80;
    server_name your-domain.com;

    # Static Frontend Assets
    location / {
        root /path/to/Contract-Risk-Intelligence/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API Proxy with Rate Limiting
    location /api/ {
        limit_req zone=contractlens_limit burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Upload file size limit (matches backend MAX_FILE_SIZE_MB=25)
        client_max_body_size 25M;
    }
}
```

## 📋 How In-Memory State Works

Since ContractLens uses **zero database dependencies**, understanding the in-memory lifecycle is important:

1. **Upload**: File is saved to `uploads/`, parsed into text, chunked with metadata (page numbers, sections), and embedded via Gemini API
2. **Indexing**: Chunk embeddings are added to a per-contract FAISS `IndexFlatIP` instance stored in Python memory
3. **Analysis**: Contract text is sent to Gemini for clause-level risk analysis; results are cached in a Python dictionary
4. **Q&A**: User queries are embedded, searched against FAISS, and relevant chunks are passed to Gemini as grounded evidence
5. **Restart**: All in-memory state (chunks, embeddings, FAISS indexes, analyses, chat history) is lost on server restart. Re-upload contracts to rebuild the index.

## 🌐 Model Context Protocol (MCP) External Legal Research

ContractLens integrates the **Model Context Protocol (MCP)** using the official Python MCP SDK (`mcp`) to enable Google Gemini to search real-time external legal authorities, statutes, and judicial precedents while evaluating uploaded contracts.

### 🏛 MCP Architecture & Request Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ContractLens Q&A Pipeline                             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                User Inquiry (e.g. "Is ₹2L bond enforceable in India?")
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │  In-Memory FAISS Vector Index │
                       │    (Contract Clause Excerpts) │
                       └───────────────┬───────────────┘
                                       │
                        Retrieved Contract Citations
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │ Research Mode Decision Controller │
                     │  - document_only                  │
                     │  - auto (detects enforceability)  │
                     │  - external_research              │
                     └─────────────────┬─────────────────┘
                                       │
              ┌────────────────────────┴────────────────────────┐
     [document_only / no legal keywords]            [external_research / auto legal query]
              │                                                 │
              │                                                 ▼
              │                              ┌─────────────────────────────────────┐
              │                              │  MCP Client Service (mcp SDK)       │
              │                              │  - Tool Discovery & Allowlist Check │
              │                              │  - JSON Schema Argument Validation  │
              │                              │  - SSRF URL Sanitization            │
              │                              └──────────────────┬──────────────────┘
              │                                                 │
              │                                 stdio / SSE Transport Execution
              │                                                 │
              │                                                 ▼
              │                              ┌─────────────────────────────────────┐
              │                              │ Configured MCP Search Server        │
              │                              │ e.g. @modelcontextprotocol/         │
              │                              │      server-brave-search            │
              │                              └──────────────────┬──────────────────┘
              │                                                 │
              │                                  Verified External Legal Sources
              │                                  (Statutes, Case Law, Judgments)
              │                                                 │
              └────────────────────────┬────────────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │    Gemini LLM Synthesis Engine  │
                      │  <UNTRUSTED_CONTRACT_EVIDENCE>  │
                      │  <UNTRUSTED_EXTERNAL_RESEARCH>  │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │ Grounded Legal Answer Breakdown:  │
                     │ 1. Contract Clause Findings       │
                     │ 2. External Legal Principles      │
                     │ 3. Practical Implications         │
                     │ 4. Uncertainties & Legal Notice   │
                     │ 5. Verified Citations & URLs      │
                     └───────────────────────────────────┘
```

---

### ⚙️ Setting Up an MCP Search Server

ContractLens supports both **stdio** (subprocess command) and **SSE** (Server-Sent Events over HTTP) transports.

#### Option A: Official Brave Search MCP Server (Recommended)

1. Ensure **Node.js 18+** and `npx` are installed on your machine (`npx --version`).
2. Obtain a free Brave Search API key from [brave.com/search/api](https://brave.com/search/api/).
3. In `backend/.env`, configure:
   ```ini
   MCP_ENABLED=true
   MCP_TRANSPORT=stdio
   MCP_SERVER_COMMAND=npx
   MCP_SERVER_ARGS=-y @modelcontextprotocol/server-brave-search
   MCP_SERVER_ENV={"BRAVE_API_KEY":"your_brave_api_key_here"}
   MCP_ALLOWED_TOOLS=brave_web_search,brave_local_search
   MCP_TIMEOUT_SECONDS=15.0
   MCP_MAX_TOOL_CALLS=3
   ```

#### Option B: Standalone Search Server or SSE Transport

If using an SSE-based MCP server running on a remote port or container:
```ini
MCP_ENABLED=true
MCP_TRANSPORT=sse
MCP_SERVER_URL=http://localhost:8080/sse
MCP_ALLOWED_TOOLS=web_search,fetch_page
```

---

### 🛡 Running With and Without MCP

| Mode | Configuration | Behavior |
|------|---------------|----------|
| **MCP Enabled** | `MCP_ENABLED=true` | Full capabilities: FAISS contract RAG + live MCP external legal research with statutory cross-examination. |
| **MCP Disabled (Default)** | `MCP_ENABLED=false` | Pure contract RAG mode. In-memory FAISS indexing, risk intelligence, and conversational analysis work 100% locally with zero external network dependencies. |

*If MCP is requested in the frontend while disabled or unreachable, ContractLens gracefully degrades: it clearly notifies the user that external research was unavailable and provides an answer grounded solely in the contract excerpts.*

---

### 🔍 Research Modes in the User Interface

The React UI provides a three-way mode switcher:

1. **Auto Research (`auto`)**: Automatically analyzes the question. If the user asks about contract terms alone (e.g. *"What is the notice period in Section 4?"*), it uses fast in-memory contract RAG. If the user asks about enforceability, statutes, or legal validity (e.g. *"Is this ₹2 lakh employment bond enforceable in India?"*), it invokes the MCP search tool.
2. **External Legal Research (`external_research`)**: Forces live external search via MCP tools to fetch statutory sections, court judgments, and legal precedents.
3. **Contract Only (`document_only`)**: Bypasses MCP entirely and answers strictly from the in-memory FAISS contract embeddings.

---

### 🔧 Troubleshooting MCP Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| **MCP Offline badge in UI** | `MCP_ENABLED=false` or server command failed | Verify `MCP_ENABLED=true` in `backend/.env` and check `GET /api/mcp/status` in your browser for detailed diagnostics. |
| **`npx: command not found`** | Node.js is not on PATH in backend shell | Verify `node -v` and `npx -v`. Specify absolute path in `MCP_SERVER_COMMAND` if needed (e.g. `C:\Program Files\nodejs\npx.cmd`). |
| **Tool timed out after 15s** | Slow network or hanging MCP subprocess | Increase `MCP_TIMEOUT_SECONDS=30.0` in `backend/.env`. |
| **`PermissionError: Tool not in approved allowlist`** | Discovered tool is not listed in `MCP_ALLOWED_TOOLS` | Add the tool name to `MCP_ALLOWED_TOOLS` in `backend/.env` (comma-separated). |
| **`Unsafe or internal URL rejected`** | SSRF protection tripped by private IP | ContractLens intentionally blocks internal IP ranges (`127.0.0.1`, `localhost`, `10.x`, `192.168.x`) to prevent server-side request forgery. |

---

### ⚖️ Legal Research Limitations & Disclaimer

- **Informational Purpose Only**: ContractLens provides AI-assisted contract risk intelligence and automated legal research. It does **not** provide formal legal counsel or binding legal conclusions.
- **Enforceability Nuances**: The enforceability of clauses (such as employment bonds, liquidated damages, or non-compete covenants) depends heavily on factual circumstances, specific training expenditures, and judicial discretion.
- **Untrusted External Data**: All retrieved external pages are treated as untrusted data (`<UNTRUSTED_EXTERNAL_RESEARCH>`) and subject to strict anti-prompt-injection isolation.
- **Statutory Verification**: Always consult a licensed attorney or jurisdictional advocate for binding legal opinions.

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite 5, Tailwind CSS 3, Lucide Icons |
| **Backend** | Python 3.10+, FastAPI, Pydantic v2, Python MCP SDK (`mcp`) |
| **AI/LLM** | Google Gemini (gemini-2.0-flash) via `google-genai` SDK |
| **Embeddings** | Google Gemini (text-embedding-004), 768-dimensional |
| **External Research** | Model Context Protocol (MCP) stdio/SSE client with schema validation |
| **Vector Search** | FAISS `IndexFlatIP` (cosine similarity via inner product) |
| **Document Parsing** | PyMuPDF (PDF), python-docx (DOCX) |
| **Storage** | In-memory Python dicts + local filesystem for uploads (Zero DB) |
| **Testing** | pytest + pytest-asyncio with mocked MCP and Gemini calls |

## 📄 License

This project is for educational and demonstration purposes. See the repository for license details.
