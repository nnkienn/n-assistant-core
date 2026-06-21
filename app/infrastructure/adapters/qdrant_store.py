from __future__ import annotations

import uuid

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.domain.ports.vector_store import SearchHit


logger = structlog.get_logger(__name__)


class QdrantStore:
    def __init__(self, url: str | None = None) -> None:
        self._client = QdrantClient(url or settings.QDRANT_URL)

    def ensure_collection(self, collection: str, dim: int) -> None:
        if not self._client.collection_exists(collection):
            self._client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info("collection_created", collection=collection, dim=dim)
    def upsert(self, collection, vectors, payloads) -> int:
        points: list[PointStruct] = []
        for vector, payload in zip(vectors, payloads):
            key = f"{payload.get('tenant_id', '')}:{payload.get('text', '')}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, key))
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        self._client.upsert(collection_name=collection, points=points)
        return len(points)
    
    def search(self, collection, query_vector, *, tenant_id, top_k=5) -> list[SearchHit]:
        namespace_filter = Filter(
            must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
        )
        results = self._client.query_points(
            collection_name=collection,
            query=query_vector,
            query_filter=namespace_filter,
            limit=top_k,
        ).points
        return [
            SearchHit(id=p.id, score=p.score, payload=p.payload or {}) for p in results
        ]
