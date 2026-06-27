from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass
class RetrievalHit:
    doc_id: str
    text: str
    score: float
    source: str


class RetrieverPort(Protocol):
    def retrieve(self, query: str, *, tenant_id: str, top_k: int = 5) -> list[RetrievalHit]: ...
