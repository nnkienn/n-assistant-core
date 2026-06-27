from __future__ import annotations
from typing import Protocol

from app.domain.ports.retriever import RetrievalHit


class Reranker(Protocol):
    def rerank(self, query: str, hits: list[RetrievalHit], *, top_k: int = 5) -> list[RetrievalHit]: ...
