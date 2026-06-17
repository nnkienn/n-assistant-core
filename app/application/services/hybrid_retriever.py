# app/application/services/hybrid_retriever.py

from app.domain.ports.retriever import RetrievalHit
from app.application.bm25_index import BM25Index  # BUG FIX: bm25_index.py nằm ở application/, không phải services/
from app.application.services.rrf import reciprocal_rank_fusion


class HybridRetriever:
    def __init__(self, embedder, vector_store, bm25_index: BM25Index) -> None:
        self._embedder     = embedder
        self._vector_store = vector_store
        self._bm25         = bm25_index

    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str,
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        # 1. dense search — Qdrant trả về ranked list theo cosine
        query_vec    = self._embedder.embed([query])[0]
        dense_hits   = self._vector_store.search(
            "chunks", query_vec, tenant_id=tenant_id, top_k=top_k * 2
        )
        dense_ranked = [h.id for h in dense_hits]

        # 2. sparse search — BM25 trả về ranked list theo keyword
        bm25_hits    = self._bm25.search(query, tenant_id=tenant_id, top_k=top_k * 2)
        bm25_ranked  = [doc_id for doc_id, _ in bm25_hits]

        # 3. RRF fuse 2 list → final ranked list
        fused = reciprocal_rank_fusion([dense_ranked, bm25_ranked])

        # 4. lấy top_k, map id → text từ dense hits
        id_to_hit = {h.id: h for h in dense_hits}
        results: list[RetrievalHit] = []
        for doc_id, score in fused[:top_k]:
            if doc_id in id_to_hit:
                h = id_to_hit[doc_id]
                results.append(RetrievalHit(
                    doc_id=doc_id,
                    text=h.payload.get("text", ""),
                    score=score,
                    source=h.payload.get("source", ""),
                ))
        return results