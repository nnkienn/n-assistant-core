from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass
class VectorSearchResult:
    id: str
    score: float
    payload: dict


class VectorStore(Protocol):
    def ensure_collection(self, name: str, dim: int) -> None: ...

    def upsert(
        self,
        collection: str,
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> int: ...

    def search(
        self,
        collection: str,
        vector: list[float],
        *,
        tenant_id: str,
        top_k: int = 5,
    ) -> list[VectorSearchResult]: ...
