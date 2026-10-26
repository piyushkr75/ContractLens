import shutil
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api.deps import (
    get_embedding_service,
    get_memory_store,
    get_settings,
)
from app.config import Settings
from app.core.memory_store import InMemoryContractStore
from app.models.schemas import (
    ContractSummary,
    ContractUploadResponse,
    DocumentChunk,
)
from app.services.document_processor import (
    DocumentProcessor,
    CorruptedFileError,
    EmptyDocumentError,
    FileValidationError,
    FileTooLargeError,
    PathTraversalError,
    ScannedPDFError,
    resolve_safe_path,
    sanitize_filename,
)
from app.services.embedding_service import GeminiEmbeddingService
from app.services.vector_store import FaissInMemoryIndex

router = APIRouter(prefix="/contracts", tags=["Contracts"])


def safe_unlink(path: Path):
    """Safely unlinks a file with garbage collection fallback on Windows."""
    try:
        if path.exists():
            path.unlink(missing_ok=True)
    except PermissionError:
        import gc
        gc.collect()
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
    except Exception:
        pass


@router.post("/upload", response_model=ContractUploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    store: InMemoryContractStore = Depends(get_memory_store),
    embedding_svc: GeminiEmbeddingService = Depends(get_embedding_service),
):
    """
    Upload a commercial contract (PDF or DOCX).
    Enforces safe filenames and path traversal protection,
    validates file magic bytes and size, extracts text using PyMuPDF and python-docx,
    preserves page numbers and section headers, and builds an in-memory FAISS index.
    Uploaded files are stored locally only and never sent to Gemini unnecessarily.
    """
    raw_filename = file.filename or "contract.txt"
    safe_filename = sanitize_filename(raw_filename)

    # Validate extension
    suffix = Path(safe_filename).suffix.lower()
    if suffix not in [".pdf", ".docx", ".doc", ".txt", ".md"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Please upload a valid PDF or DOCX file.",
        )

    # Ensure uploads directory exists and is protected
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    contract_id = str(uuid.uuid4())
    stored_name = f"{contract_id}_{safe_filename}"

    # Path traversal validation
    try:
        file_path = resolve_safe_path(upload_dir, stored_name)
    except PathTraversalError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Read content with size check and header validation
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    file_bytes = bytearray()

    try:
        # Stream file in chunks to prevent unbounded memory allocation
        chunk_read_size = 1024 * 1024  # 1MB chunks
        while True:
            chunk = await file.read(chunk_read_size)
            if not chunk:
                break
            file_bytes.extend(chunk)
            if len(file_bytes) > max_bytes:
                raise FileTooLargeError(
                    f"File exceeds maximum allowed upload size of {settings.MAX_FILE_SIZE_MB}MB."
                )

        # Magic byte content validation
        DocumentProcessor.validate_file_content(bytes(file_bytes), safe_filename)

        # Write to local uploads directory (non-public local storage)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

    except FileTooLargeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (FileValidationError, EmptyDocumentError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CorruptedFileError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to receive file: {str(e)}")

    file_size = len(file_bytes)

    # Parse document with PyMuPDF / python-docx preserving pages and section headings
    processor = DocumentProcessor(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

    try:
        blocks, full_text = processor.extract_structured_blocks(file_path, safe_filename)
        chunks = processor.chunk_document(contract_id, safe_filename, blocks, full_text)
    except (EmptyDocumentError, ScannedPDFError, CorruptedFileError) as e:
        safe_unlink(file_path)
        raise HTTPException(status_code=422, detail=str(e))
    except FileValidationError as e:
        safe_unlink(file_path)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_unlink(file_path)
        raise HTTPException(
            status_code=422,
            detail=f"Error parsing contract: {str(e)}",
        )

    if not chunks:
        safe_unlink(file_path)
        raise HTTPException(
            status_code=422, detail="Unable to create text chunks from the ingested document."
        )

    # Compute vector embeddings and index into in-memory FAISS
    # Note: Only chunk texts are embedded into FAISS; raw document is not sent to LLM unnecessarily
    chunk_texts = [c.text for c in chunks]
    embeddings = embedding_svc.get_embeddings(chunk_texts)

    faiss_index = FaissInMemoryIndex(dimension=settings.GEMINI_EMBEDDING_DIMENSION)
    faiss_index.add_chunks(chunks, embeddings)

    # Store document objects in memory store
    store.add_contract(
        contract_id=contract_id,
        filename=safe_filename,
        file_path=str(file_path),
        file_size=file_size,
        raw_text=full_text,
        chunks=chunks,
    )
    store.set_vector_index(contract_id, faiss_index)

    return ContractUploadResponse(
        contract_id=contract_id,
        filename=safe_filename,
        file_size_bytes=file_size,
        total_characters=len(full_text),
        total_chunks=len(chunks),
        uploaded_at=store.contracts[contract_id]["uploaded_at"],
        message="Document ingested, verified with PyMuPDF/python-docx, and indexed in FAISS.",
    )


@router.get("", response_model=List[ContractSummary])
def list_contracts(store: InMemoryContractStore = Depends(get_memory_store)):
    """List all currently active contracts stored in memory."""
    return store.list_contracts()


@router.get("/{contract_id}")
def get_contract_detail(
    contract_id: str, store: InMemoryContractStore = Depends(get_memory_store)
):
    """Retrieve contract details and raw content from memory."""
    contract = store.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found in memory.")
    chunks = store.get_chunks(contract_id)
    analysis = store.get_analysis(contract_id)
    return {
        "contract_id": contract["contract_id"],
        "filename": contract["filename"],
        "file_size_bytes": contract["file_size_bytes"],
        "uploaded_at": contract["uploaded_at"],
        "total_chunks": len(chunks),
        "raw_text_preview": contract["raw_text"][:2000],
        "raw_text": contract["raw_text"],
        "has_analysis": analysis is not None,
    }


@router.get("/{contract_id}/chunks", response_model=List[DocumentChunk])
def get_contract_chunks(
    contract_id: str, store: InMemoryContractStore = Depends(get_memory_store)
):
    """Retrieve all indexed chunks with page numbers, section headers, and chunk IDs."""
    contract = store.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found in memory.")
    return store.get_chunks(contract_id)


@router.get("/{contract_id}/download")
def download_contract_file(
    contract_id: str, store: InMemoryContractStore = Depends(get_memory_store)
):
    """Stream local document file for preview in browser."""
    from fastapi.responses import FileResponse
    contract = store.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")
    file_path = Path(contract["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on local storage.")
    return FileResponse(file_path, filename=contract["filename"])



@router.delete("/{contract_id}")
def delete_contract(
    contract_id: str, store: InMemoryContractStore = Depends(get_memory_store)
):
    """Delete contract from in-memory state and remove local uploaded file."""
    contract = store.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    file_path = Path(contract["file_path"])
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass

    store.delete_contract(contract_id)
    return {"message": f"Contract {contract_id} deleted from memory."}
