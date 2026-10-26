import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.schemas import (
    ChatMessage,
    ContractAnalysisResponse,
    ContractComparisonResponse,
    ContractSummary,
    DocumentChunk,
)


class InMemoryContractStore:
    """
    Central in-memory state repository for ContractLens.
    No database is used: contracts, document chunks, vector embeddings,
    FAISS indexes, risk analyses, comparisons, and conversation threads are kept in memory.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # contract_id -> dict with metadata & raw_text
        self.contracts: Dict[str, Dict[str, Any]] = {}
        # contract_id -> list of DocumentChunk
        self.chunks: Dict[str, List[DocumentChunk]] = {}
        # contract_id -> FAISS index wrapper (see services/vector_store.py)
        self.vector_indexes: Dict[str, Any] = {}
        # contract_id -> ContractAnalysisResponse
        self.analyses: Dict[str, ContractAnalysisResponse] = {}
        # comparison_key (id_a:id_b) -> ContractComparisonResponse
        self.comparisons: Dict[str, ContractComparisonResponse] = {}
        # contract_id -> list of ChatMessage
        self.chat_histories: Dict[str, List[ChatMessage]] = {}
        self.startup_time = datetime.now(timezone.utc)

    def add_contract(
        self,
        contract_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        raw_text: str,
        chunks: List[DocumentChunk],
    ):
        with self._lock:
            self.contracts[contract_id] = {
                "contract_id": contract_id,
                "filename": filename,
                "file_path": file_path,
                "file_size_bytes": file_size,
                "raw_text": raw_text,
                "uploaded_at": datetime.now(timezone.utc),
            }
            self.chunks[contract_id] = chunks
            self.chat_histories[contract_id] = []

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.contracts.get(contract_id)

    def list_contracts(self) -> List[ContractSummary]:
        with self._lock:
            summaries = []
            for c_id, meta in self.contracts.items():
                chunks = self.chunks.get(c_id, [])
                analysis = self.analyses.get(c_id)
                summaries.append(
                    ContractSummary(
                        contract_id=c_id,
                        filename=meta["filename"],
                        file_size_bytes=meta["file_size_bytes"],
                        uploaded_at=meta["uploaded_at"],
                        total_chunks=len(chunks),
                        analyzed=analysis is not None,
                        overall_risk_score=analysis.overall_risk_score if analysis else None,
                        overall_risk_level=analysis.overall_risk_level if analysis else None,
                    )
                )
            return sorted(summaries, key=lambda s: s.uploaded_at, reverse=True)

    def get_chunks(self, contract_id: str) -> List[DocumentChunk]:
        with self._lock:
            return self.chunks.get(contract_id, [])

    def set_vector_index(self, contract_id: str, vector_index: Any):
        with self._lock:
            self.vector_indexes[contract_id] = vector_index

    def get_vector_index(self, contract_id: str) -> Optional[Any]:
        with self._lock:
            return self.vector_indexes.get(contract_id)

    def save_analysis(self, contract_id: str, analysis: ContractAnalysisResponse):
        with self._lock:
            self.analyses[contract_id] = analysis

    def get_analysis(self, contract_id: str) -> Optional[ContractAnalysisResponse]:
        with self._lock:
            return self.analyses.get(contract_id)

    def save_comparison(self, key: str, comparison: ContractComparisonResponse):
        with self._lock:
            self.comparisons[key] = comparison

    def get_comparison(self, key: str) -> Optional[ContractComparisonResponse]:
        with self._lock:
            return self.comparisons.get(key)

    def append_chat_message(self, contract_id: str, message: ChatMessage):
        with self._lock:
            if contract_id not in self.chat_histories:
                self.chat_histories[contract_id] = []
            self.chat_histories[contract_id].append(message)

    def get_chat_history(self, contract_id: str) -> List[ChatMessage]:
        with self._lock:
            return list(self.chat_histories.get(contract_id, []))

    def delete_contract(self, contract_id: str) -> bool:
        with self._lock:
            if contract_id in self.contracts:
                del self.contracts[contract_id]
                self.chunks.pop(contract_id, None)
                self.vector_indexes.pop(contract_id, None)
                self.analyses.pop(contract_id, None)
                self.chat_histories.pop(contract_id, None)
                # Remove comparisons involving this contract
                keys_to_del = [k for k in self.comparisons if contract_id in k.split(":")]
                for k in keys_to_del:
                    self.comparisons.pop(k, None)
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "in_memory_documents_count": len(self.contracts),
                "faiss_indexes_count": len(self.vector_indexes),
                "total_chunks_stored": sum(len(c) for c in self.chunks.values()),
                "uptime_seconds": (datetime.now(timezone.utc) - self.startup_time).total_seconds(),
            }


# Singleton in-memory store
memory_store = InMemoryContractStore()
