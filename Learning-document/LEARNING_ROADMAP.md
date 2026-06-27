# Learning Roadmap — Nyxara AI Engineering

> Tài liệu này ghi lại những gì đã học, file đã build, và kiến thức liên quan.
> Cập nhật mỗi khi hoàn thành một kỹ thuật mới.

---

## 🏛️ Ranh giới Core ↔ Cloud (SaaS)

> **Mục tiêu kép:** repo này vừa là *giáo trình AI engineering* (học đủ, không bỏ
> kỹ thuật nào), vừa là nền để *mang đi SaaS thực tế*. Giải pháp: **2 lớp tách
> bạch — không trộn.** SaaS *thêm* lớp ngoài, không *thay* gì bên trong core.

| | `n-assistant-core` (repo này, MIT) | `n-assistant-cloud` (lớp SaaS) |
|---|---|---|
| Vai trò | **Bộ não AI** — RAG, CRAG, agent, fine-tune, eval | **Vỏ thương mại** — bán được |
| Chứa | Toàn bộ lộ trình AI engineer, niche-agnostic | auth, billing, account, dashboard, API gateway, metering |
| `tenant_id` | **namespace** (kho của 1 niche) | **customer** (map account → namespace) |
| Quan hệ | *bị gọi* — phơi API | *gọi vào* API của core |
| License | MIT, fork tự do | đóng được, thương mại |

**Cầu nối:** 1 *customer* (cloud) → ánh xạ thành 1 *tenant_id namespace* (core).
Core không biết tới tiền/account; cloud không chứa logic AI.

**Vì sao tách:** (1) core sạch → học không nhiễu, fork được, đúng "constitution"
(CI reject `import stripe`/auth trong core); (2) đổi mô hình kinh doanh không đụng
bộ não; (3) "mọi lĩnh vực" = core niche-agnostic sẵn, cloud chỉ onboard theo niche.

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

### CRAG (Corrective RAG) via LangGraph — ✅ Xong

**Kiến thức học được:**
- **State machine**: `state` = "tờ giấy" chạy qua các **node** (trạm), **điền dần** từng ô.
- **Node = hàm** (`state → dict` phần cần ghi); **edge** = đường ray cố định; **conditional edge** = rẽ nhánh theo **router**.
- **grade → verdict → correct**: **LLM-as-judge** chấm CÓ/KHÔNG → đếm `relevant`/`candidates` ra CORRECT/AMBIGUOUS/INCORRECT → INCORRECT thì **tìm lại RỘNG HƠN trong kho** (in-store, không web).
- **Retry guard** (`attempts`) chặn lặp vô hạn; `async` lan truyền (grade_node async vì gọi LLM).

**Files:**

| File | Mô tả |
|---|---|
| [app/application/crag/state.py](app/application/crag/state.py) | CRAGState — TypedDict, tờ giấy chạy qua graph |
| [app/application/crag/node.py](app/application/crag/node.py) | retrieve / grade / decide / finalize / correct node (factory DI) |
| [app/application/crag/grader.py](app/application/crag/grader.py) | RelevanceGrader — LLM-as-judge chấm yes/no |
| [app/application/crag/decision.py](app/application/crag/decision.py) | decide_verdict (logic thuần) + make_router |
| [app/application/crag/graph.py](app/application/crag/graph.py) | build_crag_graph — ráp StateGraph + vòng lặp `correct → grade` |

**Tests:** 12 — grader (4) + decision (6) + graph e2e (2: test vòng lặp tự sửa + test chốt chặn).

---

## ⏳ Phase 3 (Còn lại) — 10 kỹ thuật chưa build

| # | Kỹ thuật | Học được gì | Độ ưu tiên |
|---|----------|------------|-----------|
| 1 | ~~**Cross-encoder reranking**~~ | ✅ Xong | — |
| 2 | ~~**CRAG** via LangGraph~~ | ✅ Xong | — |
| 3 | **Metadata filtering** | lọc sản phẩm trước semantic search — dùng thật trong Comment Assistant | 🔴 Cao |
| 4 | **Query Transformation** (Multi-Query + HyDE) | query↔doc space mismatch, cách mở rộng query | 🟡 Trung bình |
| 5 | **Semantic chunking** | chunk granularity ảnh hưởng retrieval thế nào | 🟡 Trung bình |
| 6 | **Parent-Child retrieval** | match chunk nhỏ, trả chunk parent lớn | 🟡 Trung bình |
| 7 | **Context Compression** | cắt nhiễu, quản lý token budget | 🟡 Trung bình |
| 8 | **Evaluation** (RAGAS + A/B) | đo xem mỗi kỹ thuật có thật sự giúp ích không | 🔴 Cao |
| 9 | **Temporal / Freshness-aware retrieval** | timestamp mỗi chunk (đã có `harvested_at` ở lớp raw) → đẩy vào payload Qdrant + recency scoring (time-decay); chunk quá cũ coi như rác dù đúng topic. **Flag theo niche:** tài chính/news = bật gắt, kiến thức ổn định = tắt | 🟡 TB (🔴 cho tài chính/news) |
| 10 | **MMR — Retrieval diversity** | Maximal Marginal Relevance: tránh top-k toàn chunk gần trùng nhau → bao phủ nhiều khía cạnh câu hỏi | 🟡 Trung bình |
| 11 | **Context-window budgeting + "lost in the middle"** | khi context + lịch sử vượt cửa sổ: cắt/sắp xếp sao; đặt chunk quan trọng ở đầu/cuối vì LLM hay bỏ quên phần giữa | 🟡 Trung bình |

---

## 🚀 Phase 3.5 — Tối ưu tốc độ truy vấn (sau khi pipeline đủ tính năng)

> **Nguyên tắc: đo trước, tối ưu sau.** Chỉ tối ưu khi pipeline đã chạy đúng và
> đã profiling thấy chỗ nghẽn. Premature optimization = bẫy kinh điển.

| # | Kỹ thuật | Học được gì |
|---|----------|------------|
| 1 | **Latency profiling** | đo từng chặng (embed / dense / sparse / rerank) trước khi đụng vào — không tối ưu mù |
| 2 | **Qdrant payload indexing** | tạo index cho `tenant_id` / `timestamp` / `parent_id` → filter nhanh thay vì full scan |
| 3 | **HNSW tuning** (`m`, `ef_construct`, `ef_search`) | đánh đổi recall ↔ latency |
| 4 | **Vector quantization** (scalar / product) | giảm RAM + tăng tốc search, mất ít recall |
| 5 | **Two-stage budget tuning** | cân `top_k` retrieve vs rerank — rerank (cross-encoder) là chặng đắt nhất |
| 6 | **Caching (Redis)** | cache embedding query + kết quả truy vấn lặp lại |
| 7 | **Async + batching** | embed/search song song, gộp batch nhiều query |
| 8 | **Semantic caching** | cache theo *ý nghĩa* query (2 câu khác chữ cùng ý → hit cache) — khác cache khớp-chữ ở #6, giảm cost/latency mạnh |

---

## 🎓 Lộ trình đầy đủ — Phase 4 → 7 (giáo trình + production-grade)

> Phần trên (Phase 0–3.5) là *đã/đang làm*. Phần dưới là *bản đồ còn lại*, gộp đủ
> kỹ thuật một sản phẩm AI **thật** cần — để không sợ "học sai/thiếu lộ trình".
> Nhãn: 🛠️ **làm tay** (học sâu) · 📡 **radar** (biết để sau, làm khi gặp lỗi thật).
> Mục thuộc **cloud** (xem §Ranh giới Core↔Cloud) được ghi rõ — không nhồi vào core.

### Phase 4 — Fine-tuning
| Kỹ thuật | Học được gì | |
|---|---|---|
| LoRA trên `Qwen2.5-7B` | low-rank update math | 🛠️ |
| GGUF quantization (Q4/Q5/Q8) merge | nén model chạy local | 🛠️ |
| Embedding / domain fine-tuning | chỉnh bge-m3 cho niche | 🛠️ |
| 🆕 **Synthetic data generation** | sinh data train khi data thật ít | 🛠️ |

### Phase 5 — Agentic Orchestrator (LangGraph)
| Kỹ thuật | Học được gì | |
|---|---|---|
| Supervisor→Researcher→Creator→Critic→Human gate | multi-agent, HITL, anti-hallucination | 🛠️ |
| 🆕 **Structured output / constrained decoding** | ép JSON hợp lệ cho tool-calling, retry khi lỗi | 🛠️ |
| 🆕 **Intent triage** | phân loại comment: trả lời / lờ / đẩy người — tiết kiệm LLM | 🛠️ |
| 🆕 **Multi-turn / thread memory** | nhớ ngữ cảnh hội thoại, không single-shot | 🛠️ |
| 🆕 **Abstention "tôi không biết"** | từ chối có hiệu chỉnh thay vì đoán bừa | 🛠️ |
| 🆕 **Human-feedback → training loop** | edit của người duyệt → data train (active learning) | 📡 |

### 🆕 Phase 5.5 — Safety & Guardrails (áo giáp an toàn)
| Kỹ thuật | Học được gì | Lớp |
|---|---|---|
| **Prompt injection defense** | chặn input độc lái agent (UGC không tin được) | core |
| **PII redaction** | phát hiện + che SĐT/địa chỉ (PDPD/GDPR) | core |
| **Toxicity / moderation** (in + out) | lọc chửi bới 2 chiều | core |
| **Red-teaming / jailbreak testing** | tự tấn công tìm lỗ trước kẻ xấu | core |
| **Output guardrail framework** | tầng policy có hệ thống (ngoài Critic) | core |
| **Graceful degradation** | Qdrant/LLM sập → xuống cấp êm | core |
| **Cost / rate guard + circuit breaker** | chặn nổ bill | core *đo* · **cloud** *enforce theo customer* |

### Phase 6 — Production, MLOps & Eval-at-scale
| Kỹ thuật | Học được gì | |
|---|---|---|
| Observability: LangFuse · Prometheus + Grafana | trace, metric, log | 🛠️ |
| 🆕 **Data Lifecycle**: vector CRUD/delete/sync · dedup · incremental ingest · **embedding migration (re-embed khi đổi model)** | giữ kho đúng theo thời gian | 🛠️ |
| 🆕 **Eval-at-scale**: online eval · golden/regression set · prompt versioning · LLM-judge calibration | đo chất lượng production, chống tụt khi đổi prompt/model | 🛠️ |
| CI/CD retrain · experiment tracking (W&B/MLflow) · versioning (DVC/HF) | reproducible ML | 📡 |
| 🆕 Canary/blue-green model deploy · DR/backup · scaling/backpressure | tung model an toàn, chịu tải | 📡 (nhiều phần **cloud**) |
| 🆕 Data retention / right-to-be-forgotten | xóa data theo yêu cầu (luật) | 📡 (**cloud**) |

### Phase 7 — Community & Extensibility
| Kỹ thuật | Học được gì | |
|---|---|---|
| Niche templates · plugin (scraper / LLM client) | mở rộng open-source | 🛠️ |
| 🆕 **Analytics feedback loop (Analyst role)** | engagement → "cái gì hiệu quả" vào memory niche | 📡 |
| 🆕 **AI disclosure / watermarking** | ghi rõ nội dung AI (luật/nền tảng) | 📡 (**cloud**) |
| 🆕 **Bias / fairness audit** | model đối xử công bằng giữa nhóm/sản phẩm | 📡 |

### ★ Visual & Character Engine — OPTIONAL (cần GPU, off main path)
ComfyUI · Flux/SDXL · ControlNet · IP-Adapter/FaceID · character LoRA · img/text→video · TTS clone (XTTS/CosyVoice) · ffmpeg auto-edit.

### 📡 Radar nâng cao — mẻ cuối (biết để có, làm khi cần)
> Frontier/optional. Phần lớn là biến thể của cái đã có — **đừng để chúng chặn việc build.**

| Kỹ thuật | Slot | Ghi chú |
|---|---|---|
| **Prompt engineering craft** (CoT, few-shot, dynamic example selection) | P5 nền | kỹ năng nền nhất — gọi tên hẳn thay vì ngầm định |
| **Adaptive-RAG / Self-RAG** | P3 | quyết định *có nên retrieve không* ngay từ đầu — anh em ruột với CRAG |
| **Query routing** (multi-source / multi-tool) | P5 | chọn kho/tool nào khi có nhiều nguồn — sâu hơn intent triage |
| **GraphRAG** (knowledge graph, multi-hop) | P3 | câu hỏi nối nhiều mẩu; vector thuần yếu chỗ này |
| **Multimodal RAG** (ảnh / bảng / PDF) | P3 | ảnh sản phẩm e-commerce, transcript đa phương thức |
| **Self-consistency / SelfCheckGPT** | P5.5 | phát hiện bịa bằng sample nhiều lần so chéo — khác abstention |
| **Drift detection** (data / embedding / concept drift) | P6 | đo chất lượng tụt âm thầm theo thời gian |
| **Output sanitization** (XSS / markdown injection trong reply) | P5.5 | làm sạch *output* trước khi render/gửi — khác injection input |
| **MCP (Model Context Protocol)** | P5 | chuẩn hiện đại gắn tool/context cho agent |

---

## 🎯 Nguyên tắc: Học vs. Production

> Project này build **tất cả** kỹ thuật để **HỌC cho biết** — nhưng một sản phẩm
> thật **KHÔNG dùng hết**. Mỗi fork chỉ **bật đúng subset** niche của nó cần (vì
> vậy mọi kỹ thuật là *flag, mặc định TẮT* — `tech-stack-rule §5.4`).
>
> Học hết là để **có phán đoán** chọn đúng — không thể chọn khôn ngoan nếu chưa
> từng build + đo từng cái. **Eval (Phase 3)** cho biết cái nào *thật sự đáng bật*.
> **Học một kỹ thuật ≠ phải deploy nó.**

---

## 📊 Tổng kết Tests

```
68 tests passed — 0 failed
├── Phase 2 infrastructure:  15 tests
├── Phase 3 BM25:            13 tests
├── Phase 3 RRF:             10 tests
├── Phase 3 HybridRetriever: 11 tests
├── Phase 3 CRAG:            12 tests  (grader 4 · decision 6 · graph e2e 2)
└── Other (chunker, ingestion, api): 7 tests
```

---

## 📚 Tài liệu tham khảo

| Tài liệu | Nội dung |
|----------|---------|
| [GLOSSARY.md](GLOSSARY.md) | **Bảng tra thuật ngữ nhanh** — quên từ nào tra 1 dòng ở đây |
| [notes-knowledge.md](notes-knowledge.md) | Công thức + giải thích khái niệm Phase 2 & 3 |
| [README.vi.md](README.vi.md) | Roadmap dự án đầy đủ, kiến trúc hệ thống |
| Cormack et al. 2009 | Paper gốc RRF — `k=60` từ đây |
| Robertson et al. 1994 | Paper gốc Okapi BM25 |
| BAAI/bge-m3 | Model embedding 1024-dim, 100+ ngôn ngữ |
