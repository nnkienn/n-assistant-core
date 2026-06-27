"""BGEReranker — cross-encoder reranking dùng BAAI/bge-reranker-v2-m3.

VI: Cross-encoder đọc query + doc CÙNG NHAU trong 1 forward pass.
    Khác với bi-encoder (bge-m3) đọc query và doc riêng lẻ rồi so vector.

EN: Cross-encoder reads query + doc TOGETHER in one forward pass.
    Unlike bi-encoder (bge-m3) which encodes query and doc separately then compares vectors.

Bi-encoder vs Cross-encoder:
    Bi-encoder (bge-m3):
        encode("kem dưỡng da") → vector_A
        encode("moisturizing cream") → vector_B
        cosine(vector_A, vector_B) = 0.92   ← so sánh gián tiếp
        Nhanh — precompute doc vectors, store trong Qdrant.

    Cross-encoder (bge-reranker-v2-m3):
        score(["kem dưỡng da dầu", "Neutrogena không gây bít lỗ chân lông"]) = 0.94
        score(["kem dưỡng da dầu", "Kem dưỡng ẩm cho da khô"]) = 0.21
        Chậm hơn — không thể precompute, phải chạy lúc query time.
        Chính xác hơn — hiểu interaction giữa query và doc.

Tại sao vẫn cần HybridRetriever trước? / Why still need HybridRetriever first?
    VI: Cross-encoder chạy O(n) forward passes — quá chậm nếu chạy trên 10,000 docs.
        HybridRetriever lọc nhanh xuống còn top 20, cross-encoder chỉ chạy 20 lần.
    EN: Cross-encoder runs O(n) forward passes — too slow on 10,000 docs.
        HybridRetriever quickly filters to top 20, cross-encoder only runs 20 times.

Xem thêm / See also: LEARNING_ROADMAP.md §Cross-encoder reranking
"""

from __future__ import annotations

import structlog
from FlagEmbedding import FlagReranker

from app.domain.ports.retriever import RetrievalHit

logger = structlog.get_logger(__name__)


class BGEReranker:
    """Cross-encoder reranker dùng bge-reranker-v2-m3 (cùng họ bge-m3)."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        *,
        use_fp16: bool = False,
    ) -> None:
        # VI: FlagReranker load model cross-encoder — nặng hơn FlagEmbedder một chút.
        #     Build ONCE per process, reuse — không tạo mới mỗi request.
        # EN: FlagReranker loads the cross-encoder model — slightly heavier than FlagEmbedder.
        #     Build ONCE per process, reuse — never instantiate per request.
        logger.info("loading_reranker", model=model_name)
        self._model = FlagReranker(model_name, use_fp16=use_fp16)

    def rerank(
        self,
        query: str,
        hits: list[RetrievalHit],
        *,
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        if not hits:
            return []

        # VI: Tạo pairs [query, doc_text] cho từng hit — đây là input của cross-encoder.
        #     Cross-encoder đọc cả 2 cùng lúc trong 1 forward pass.
        # EN: Create [query, doc_text] pairs for each hit — this is the cross-encoder input.
        #     Cross-encoder reads both together in one forward pass.
        pairs = [[query, hit.text] for hit in hits]

        # VI: compute_score trả về list[float] — 1 score cho mỗi pair.
        #     Score càng cao = doc càng liên quan đến query.
        # EN: compute_score returns list[float] — 1 score per pair.
        #     Higher score = doc more relevant to query.
        scores = self._model.compute_score(pairs)

        # VI: Gắn score mới vào từng hit rồi sort giảm dần.
        #     Score cũ (RRF score) bị thay thế bởi cross-encoder score.
        # EN: Attach new score to each hit then sort descending.
        #     Old score (RRF score) is replaced by cross-encoder score.
        reranked = sorted(
            zip(hits, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            RetrievalHit(
                doc_id=hit.doc_id,
                text=hit.text,
                score=float(score),   # VI: cross-encoder score / EN: cross-encoder score
                source=hit.source,
            )
            for hit, score in reranked[:top_k]
        ]
