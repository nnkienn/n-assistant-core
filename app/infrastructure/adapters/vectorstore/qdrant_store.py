from __future__ import annotations
import uuid 
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.domain.ports.vector_store import VectorSearchResult

class QdrantStore:
    def __init__ (self, host: str = "localhost", port: int = 6333) -> None:
        self._client = QdrantClient(host=host, port=port)
    def ensure_collection(self, name: str, dim: int) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if name not in existing:
            self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
    def upsert(
        self,
        collection: str,
        vectors: list[list[float]],
        payloads: list[dict],
    )-> int :
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, p.get("text", "") + p.get("tenant_id", ""))),
                vector=v,
                payload=p,
            )
            for v, p in zip(vectors, payloads)
        ]
        self._client.upsert(collection_name=collection, points=points)
        return len(points)

    def search(self, collection: str2222.
               , vector: list[float], *, tenant_id: str, top_k: int = 5) -> list[VectorSearchResult]:
        hits = self._client.search(
            collection_name=collection,
            query_vector=vector,
            query_filter=Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]),
            limit=top_k,
        )
        return [VectorSearchResult(id=h.id, score=h.score, payload=h.payload or {}) for h in hits]