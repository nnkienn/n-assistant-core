# Learning Roadmap — Nyxara AI Engineering

> Tài liệu này ghi lại những gì đã học, file đã build, và kiến thức liên quan.
> Cập nhật mỗi khi hoàn thành một kỹ thuật mới.

---

## ✅ Phase 2 — Vector Memory

### Kiến thức học được
- **Vector Embedding**: ánh xạ text → vector 1024 chiều bằng contrastive learning. Không phải hash — là learned representation từ hàng tỷ cặp câu.
- **Cosine Similarity**: đo góc giữa 2 vector, invariant với magnitude. L2-normalized → rút gọn thành dot product.
- **Tenant Isolation**: single-collection multi-tenancy với mandatory `tenant_id` filter. Silent failure nếu bỏ filter.

### Files đã build

| File | Mô tả |
|------|-------|
| [app/infrastructure/adapters/bge_embedder.py](app/infrastructure/adapters/bge_embedder.py) | BGEEmbedder — load BAAI/bge-m3, embed batch text → list[list[float]] |
| [app/infrastructure/adapters/qdrant_store.py](app/infrastructure/adapters/qdrant_store.py) | QdrantStore — ensure_collection, upsert (idempotent UUID5), search với tenant filter |
| [app/domain/ports/embedder.py](app/domain/ports/embedder.py) | Embedder Protocol — dim property + embed() method |
| [app/domain/ports/vector_store.py](app/domain/ports/vector_store.py) | VectorStore Protocol — SearchHit dataclass |

### Tests

| File | Tests |
|------|-------|
| [tests/infrastructure/adapters/test_bge_embedder.py](tests/infrastructure/adapters/test_bge_embedder.py) | 6 tests — dim, empty guard, list[list[float]], 1024 dims, batch, return_dense=True |
| [tests/infrastructure/adapters/test_qdrant_store.py](tests/infrastructure/adapters/test_qdrant_store.py) | 9 tests — ensure idempotent, upsert count, UUID5 deterministic, tenant filter, SearchHit, None payload |

---

## ✅ Phase 3 (Partial) — Advanced RAG

### Kiến thức học được

**TF-IDF vs BM25**
- TF = số lần term xuất hiện trong 1 doc. IDF = độ hiếm trên toàn corpus.
- TF-IDF: 2 vấn đề — TF không có saturation + không chuẩn hóa độ dài doc.
- BM25 giải quyết bằng `k1` (TF saturation) và `b` (length normalization).

**BM25 Formula**
```
score(d,t) = IDF(t) × TF×(k1+1) / (TF + k1×(1-b+b×dl/avgdl))
IDF(t)     = log((N - df + 0.5) / (df + 0.5) + 1)
k1 = 1.5  →  TF saturation
b  = 0.75 →  length normalization
```

**RRF — Reciprocal Rank Fusion**
- Cosine similarity: [0,1]. BM25 score: [0,∞). Không cùng đơn vị → không cộng trực tiếp.
- RRF chuyển cả 2 về rank → scale-invariant.
```
RRF(d) = Σ  1 / (k + rank_i(d))    k=60 (Cormack 2009)
```

**HybridRetriever Flow**
```
query
  ├─→ embed(query) → Qdrant cosine search (top 2k) → dense_ranked
  ├─→ BM25.search(query, tenant_id) (top 2k)        → bm25_ranked
  └─→ RRF([dense_ranked, bm25_ranked])               → top_k RetrievalHit
```

### Files đã build

| File | Mô tả |
|------|-------|
| [app/application/bm25_index.py](app/application/bm25_index.py) | BM25Index — in-memory sparse search, tenant isolation, Okapi BM25 formula |
| [app/application/services/rrf.py](app/application/services/rrf.py) | reciprocal_rank_fusion() — gộp N ranked lists, k=60 damping |
| [app/application/services/hybrid_retriever.py](app/application/services/hybrid_retriever.py) | HybridRetriever — orchestrates dense + sparse + RRF |
| [app/domain/ports/retriever.py](app/domain/ports/retriever.py) | RetrieverPort Protocol + RetrievalHit dataclass |

### Tests

| File | Tests |
|------|-------|
| [tests/application/test_bm25_index.py](tests/application/test_bm25_index.py) | 13 tests — relevance, ranking, top_k, tenant isolation, TF boost, case-insensitive, IDF |
| [tests/application/test_rrf.py](tests/application/test_rrf.py) | 10 tests — ranking, cross-list boost, formula 1/61, equal scores, k parameter, accumulation |
| [tests/application/services/test_hybrid_retriever.py](tests/application/services/test_hybrid_retriever.py) | 11 tests — output type, top_k, embedder called, tenant isolation, RRF boost |

---

### Cross-encoder Reranking — bge-reranker-v2-m3

**Kiến thức học được:**
- **Bi-encoder vs Cross-encoder**: bi-encoder encode query và doc riêng lẻ rồi so vector. Cross-encoder đọc query + doc cùng nhau trong 1 forward pass → chính xác hơn nhưng chậm hơn.
- **Tại sao cần 2 bước**: HybridRetriever lọc nhanh top-20 → cross-encoder chấm kỹ top-5. Không thể chạy cross-encoder trên toàn bộ 10,000 docs.
- **Score thay thế**: RRF score bị thay bằng cross-encoder relevance score.

**Pipeline đầy đủ sau khi có reranker:**
```
query
  ├─→ HybridRetriever (nhanh) → top 20 candidates
  └─→ BGEReranker (chính xác) → top 5 final
```

**Files:**

| File | Mô tả |
|------|-------|
| [app/domain/ports/reranker.py](app/domain/ports/reranker.py) | Reranker Protocol |
| [app/infrastructure/adapters/bge_reranker.py](app/infrastructure/adapters/bge_reranker.py) | BGEReranker — FlagReranker, compute_score pairs |
| [tests/infrastructure/adapters/test_bge_reranker.py](tests/infrastructure/adapters/test_bge_reranker.py) | 6 tests — sort, score replace, top_k, pairs, fields |

---

## ⏳ Phase 3 (Còn lại) — 7 kỹ thuật chưa build

| # | Kỹ thuật | Học được gì | Độ ưu tiên |
|---|----------|------------|-----------|
| 1 | ~~**Cross-encoder reranking**~~ | ✅ Xong | — |
| 2 | **CRAG** via LangGraph | self-grading context, corrective retrieval loop | 🔴 Cao |
| 3 | **Metadata filtering** | lọc sản phẩm trước semantic search — dùng thật trong Comment Assistant | 🔴 Cao |
| 4 | **Query Transformation** (Multi-Query + HyDE) | query↔doc space mismatch, cách mở rộng query | 🟡 Trung bình |
| 5 | **Semantic chunking** | chunk granularity ảnh hưởng retrieval thế nào | 🟡 Trung bình |
| 6 | **Parent-Child retrieval** | match chunk nhỏ, trả chunk parent lớn | 🟡 Trung bình |
| 7 | **Context Compression** | cắt nhiễu, quản lý token budget | 🟡 Trung bình |
| 8 | **Evaluation** (RAGAS + A/B) | đo xem mỗi kỹ thuật có thật sự giúp ích không | 🔴 Cao |

---

## 📊 Tổng kết Tests

```
56 tests passed — 0 failed
├── Phase 2 infrastructure:  15 tests
├── Phase 3 BM25:            13 tests
├── Phase 3 RRF:             10 tests
├── Phase 3 HybridRetriever: 11 tests
└── Other (chunker, ingestion, api): 7 tests
```

---

## 📚 Tài liệu tham khảo

| Tài liệu | Nội dung |
|----------|---------|
| [notes-knowledge.md](notes-knowledge.md) | Công thức + giải thích khái niệm Phase 2 & 3 |
| [README.vi.md](README.vi.md) | Roadmap dự án đầy đủ, kiến trúc hệ thống |
| Cormack et al. 2009 | Paper gốc RRF — `k=60` từ đây |
| Robertson et al. 1994 | Paper gốc Okapi BM25 |
| BAAI/bge-m3 | Model embedding 1024-dim, 100+ ngôn ngữ |
