"""Reranker port — contract for cross-encoder reranking.

VI: Reranker nhận top-k candidates từ HybridRetriever và chấm lại
    bằng cách đọc query + doc CÙNG NHAU → kết quả chính xác hơn.

EN: Reranker takes top-k candidates from HybridRetriever and re-scores
    them by reading query + doc TOGETHER → more accurate results.

Tại sao là Protocol? / Why Protocol?
    VI: Giống Embedder — có thể có nhiều implementation:
        BGEReranker (local), Cohere Rerank (cloud API), v.v.
        Caller không cần biết implementation nào đang chạy.
    EN: Like Embedder — multiple implementations are possible:
        BGEReranker (local), Cohere Rerank (cloud API), etc.
        Caller doesn't need to know which implementation is running.

Xem thêm / See also: notes-knowledge.md, LEARNING_ROADMAP.md §Cross-encoder reranking
"""

from __future__ import annotations

from typing import Protocol

from app.domain.ports.retriever import RetrievalHit


class Reranker(Protocol):

    def rerank(
        self,
        query: str,
        hits: list[RetrievalHit],
        *,
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        """Chấm lại hits theo mức độ liên quan thật sự với query.

        VI: Input là kết quả thô từ HybridRetriever (top 2k hoặc top 20).
            Output là top_k hits đã được sắp xếp lại theo cross-encoder score.
            Score mới là relevance score của cross-encoder, không phải RRF score.

        EN: Input is raw results from HybridRetriever (top 2k or top 20).
            Output is top_k hits re-sorted by cross-encoder score.
            New score is the cross-encoder relevance score, not the RRF score.
        """
        ...
