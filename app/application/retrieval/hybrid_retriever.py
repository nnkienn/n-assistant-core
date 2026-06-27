"""HybridRetriever — Orchestrates dense + sparse retrieval with RRF fusion (Phase 3).

VI: HybridRetriever là trung tâm điều phối của toàn bộ pipeline retrieval Phase 3.
    Nó kết hợp 2 nguồn retrieval độc lập rồi dùng RRF để cho ra kết quả tốt nhất.
EN: HybridRetriever is the orchestrator of the entire Phase 3 retrieval pipeline.
    It combines 2 independent retrieval sources then uses RRF to produce the best result.

Ứng dụng / Application:
    Comment Assistant dùng HybridRetriever để tìm đúng thông tin sản phẩm
    khi trả lời comment của khách hàng trên TikTok Shop / Shopee.

    Comment Assistant uses HybridRetriever to find the right product information
    when answering customer comments on TikTok Shop / Shopee.

Flow / Pipeline:
    query
      ├─→ [Dense]  bge-m3 embed → Qdrant cosine search (top 2k) → dense_ranked
      ├─→ [Sparse] BM25 keyword search (top 2k)                  → bm25_ranked
      └─→ [Fusion] RRF([dense_ranked, bm25_ranked])              → top_k RetrievalHit

Tại sao Hybrid? / Why Hybrid?
    VI: Dense search giỏi ngữ nghĩa nhưng trượt từ khóa chính xác ("SPF 50+", mã SKU).
        BM25 bắt từ khóa chính xác nhưng không hiểu ngữ nghĩa đa ngôn ngữ.
        Hybrid lấy điểm mạnh của cả hai.
    EN: Dense search handles semantics well but misses exact keywords ("SPF 50+", SKU codes).
        BM25 catches exact keywords but doesn't understand multilingual semantics.
        Hybrid takes the best of both.

Xem thêm / See also:
    notes-knowledge.md §7 RRF, §8 HybridRetriever Flow
    app/application/bm25_index.py
    app/application/services/rrf.py
"""

from app.domain.ports.retriever import RetrievalHit
from app.application.retrieval.bm25_index import BM25Index          # nằm ở application/, không phải services/
from app.application.retrieval.rrf import reciprocal_rank_fusion


class HybridRetriever:

    def __init__(self, embedder, vector_store, bm25_index: BM25Index) -> None:
        # VI: Dependency Injection — caller quyết định implementation.
        #     Test inject MagicMock, production inject BGEEmbedder + QdrantStore + BM25Index thật.
        # EN: Dependency Injection — caller decides the implementation.
        #     Tests inject MagicMock, production injects real BGEEmbedder + QdrantStore + BM25Index.
        self._embedder     = embedder
        self._vector_store = vector_store
        self._bm25         = bm25_index

    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str,   # VI: keyword-only — namespace isolation bắt buộc / EN: keyword-only — namespace isolation is mandatory
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        # ── Bước 1: Dense Search ─────────────────────────────────────────────
        # VI: Embed query thành vector rồi tìm top 2k docs gần nhất trong Qdrant.
        #     [0] vì embed() trả về list — ta chỉ embed 1 query nên lấy phần tử đầu.
        # EN: Embed the query into a vector then find the top 2k nearest docs in Qdrant.
        #     [0] because embed() returns a list — we embed 1 query so we take element 0.
        query_vec    = self._embedder.embed([query])[0]
        dense_hits   = self._vector_store.search(
            "chunks", query_vec, tenant_id=tenant_id, top_k=top_k * 2
        )
        # VI: RRF chỉ cần ranked list của id — score cosine bị bỏ qua
        # EN: RRF only needs the ranked id list — cosine scores are discarded
        dense_ranked = [h.id for h in dense_hits]

        # ── Bước 2: Sparse Search (BM25) ─────────────────────────────────────
        # VI: Tìm top 2k docs theo keyword matching. Bổ sung cho dense search:
        #     bắt được "SPF 50+", mã sản phẩm, tên riêng mà bge-m3 có thể bỏ sót.
        # EN: Find top 2k docs by keyword matching. Complements dense search:
        #     catches "SPF 50+", product codes, proper nouns that bge-m3 may miss.
        bm25_hits    = self._bm25.search(query, tenant_id=tenant_id, top_k=top_k * 2)
        # VI: _ bỏ BM25 score — RRF dùng rank, không dùng điểm tuyệt đối
        # EN: _ discards BM25 score — RRF uses rank, not absolute scores
        bm25_ranked  = [doc_id for doc_id, _ in bm25_hits]

        # ── Bước 3: RRF Fusion ───────────────────────────────────────────────
        # VI: Gộp 2 ranked list thành 1. Doc xuất hiện cao trong cả 2 list → score cao.
        #     Scale-invariant: không cần cosine và BM25 cùng đơn vị đo.
        # EN: Merge 2 ranked lists into 1. Doc ranking high in both lists → high score.
        #     Scale-invariant: cosine and BM25 don't need the same unit of measure.
        fused = reciprocal_rank_fusion([dense_ranked, bm25_ranked])

        # ── Bước 4: Build RetrievalHit ───────────────────────────────────────
        # VI: Sau RRF chỉ có doc_id và RRF score — cần lookup text + metadata từ dense_hits.
        #     Dict cho phép lookup O(1) thay vì linear scan.
        # EN: After RRF we only have doc_id and RRF score — need to lookup text + metadata from dense_hits.
        #     Dict allows O(1) lookup instead of linear scan.
        id_to_hit = {h.id: h for h in dense_hits}
        results: list[RetrievalHit] = []

        for doc_id, score in fused[:top_k]:
            if doc_id not in id_to_hit:
                # VI: Doc có trong BM25 nhưng không có trong dense hits → không có payload → skip
                # EN: Doc in BM25 but not in dense hits → no payload to retrieve text from → skip
                continue
            h = id_to_hit[doc_id]
            results.append(RetrievalHit(
                doc_id=doc_id,
                text=h.payload.get("text", ""),
                score=score,                          # VI: RRF score, không phải cosine / EN: RRF score, not cosine
                source=h.payload.get("source", ""),
            ))

        return results
