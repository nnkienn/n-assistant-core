"""Retriever port — domain contract for hybrid search.

RetrievalHit  : plain data object (kết quả trả về từ retriever).
RetrieverPort : structural Protocol — HybridRetriever phải implement method này.

Hexagonal rule: domain không import gì từ infrastructure (Qdrant, BM25, ...).
Caller chỉ phụ thuộc vào RetrieverPort, không phụ thuộc vào HybridRetriever.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RetrievalHit:
    """Một kết quả retrieval: id tài liệu, nội dung, điểm relevance, nguồn."""

    doc_id: str
    text: str
    score: float
    source: str


class RetrieverPort(Protocol):
    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str,
        top_k: int = 5,
    ) -> list[RetrievalHit]: ...
