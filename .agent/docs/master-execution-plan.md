# 🗺️ MASTER EXECUTION PLAN — Nyxara (V5.0, Learning Edition · Niche-Focused)

> **Scope:** the full roadmap for the **single MIT repo** `nyxara`. This is an
> open-source, modular **multilingual RAG + agentic engine, built from scratch
> as a learning vehicle**, aimed at one concrete niche: content & social
> automation for **seller-affiliates on TikTok Shop / Shopee (VN)**. There is no
> commercial layer and no SaaS productization stage.
> **First core product:** the **Comment Assistant** — read public comments under
> a selling video → RAG-retrieve the right product info → draft an on-voice
> reply → **a human approves before anything is sent** (human-in-the-loop, no
> auto-post; sending uses the platform's **official API**).
> **Companion docs:** [`product-requirements.md`](product-requirements.md) ·
> [`ai-agent-design.md`](ai-agent-design.md) ·
> [`../rules/tech-stack-rule.md`](../rules/tech-stack-rule.md).

---

## V5.0 changelog (Niche refocus)

- **Repositioning:** from "Virtual Content Factory / auto-publish without a human"
  → **multilingual RAG + agentic engine, learn-from-scratch, seller-affiliate
  niche, human-in-the-loop.** All autonomous self-publishing language removed.
- **Removed from the main path:** browser auto-posting (Playwright stealth,
  `playwright-stealth`, AES-256 session vault, scheduled auto-posting). Reason:
  it teaches no AI skill, violates platform ToS, and risks bans. When publishing
  is needed → use the **official API**.
- **Visual & Character Engine** demoted to an **OPTIONAL** track (off the main
  learning path). The agent/plugin architecture lets it be added later without
  breaking what's built.
- **Phase 3 expanded** with reranking, metadata filtering, and semantic chunking
  (full spec below) and **basic Eval (RAGAS + A/B) pulled up into Phase 3.**
- **Phases reordered** so CORE phases are contiguous: Agentic Orchestrator
  becomes Phase 5 (CORE), Production/MLOps Phase 6, Community Phase 7; Visual is
  a separate OPTIONAL track.

---

## Overall goal

A multilingual RAG + agentic engine anyone can fork and run 100% local. Each
phase is ordered to teach a layer of the stack from scratch — the math, the
architecture, and the production craft — pointed at a real niche so the learning
has a concrete destination **and** real (if small) users.

`tenant_id` is a **namespace** for hosting several niches/users in one install.
It is not customer-billing isolation. No auth, no dashboard, no monetization.

---

## Phase overview

| Phase | Track | Theme | Status |
|---|---|---|---|
| **0. Foundation** | CORE | Harvester: **product data + public comment samples**, clean MIT repo, per-niche examples | 🟢 Done |
| **1. Skeleton** | CORE | FastAPI core, `/health`, Docker, unified CLI | ✅ Done |
| **2. Vector Memory** | CORE | Chunking + `bge-m3` + Qdrant + multi-namespace | ✅ Done |
| **3. Advanced RAG + Eval** | CORE | Hybrid + RRF + **rerank** + CRAG + query-transform + parent-child + compression + **metadata filter** + **semantic chunking**, all togglable per query, with **RAGAS + A/B eval** baked in | 🚧 In progress |
| **4. Fine-tuning** | CORE | LoRA on Qwen2.5-7B, GGUF merge, multi-domain dataset, **embedding/domain fine-tuning** | ⏳ Planned |
| **5. Agentic Orchestrator** | CORE | LangGraph Supervisor–Worker (Researcher → Creator → **Critic**), **Comment Assistant** end-to-end, **human-in-the-loop**, domain router | ⏳ Planned |
| **6. Production, MLOps & Eval** | CORE | Full Docker stack, heavy MLOps (LangFuse/Prometheus/Grafana), CI/CD retrain, experiment tracking | ⏳ Planned |
| **7. Community & Extensibility** | CORE | Niche templates, plugin architecture, example projects | ⏳ Planned |
| **★ Visual & Character Engine** | **OPTIONAL** | ComfyUI consistent character, SDXL/Flux + ControlNet, video + TTS + ffmpeg | 🧩 Add-on · needs GPU |

> **Deep-learning threads running through every phase:** embedding & similarity
> math, RRF, **cross-encoder reranking**, **RAG evaluation metrics**, low-rank
> adaptation (LoRA), quantization, agentic graphs, and light MLOps.

---

## Phase 0 — Foundation (Harvester) ✅ · CORE

> **Goal:** an autonomous, scheduled subsystem that acquires **public** data and
> lands it — cleaned and `tenant_id`-tagged — ready for Qdrant, **without any LLM
> in the loop**. See [`product-requirements.md` §3.8](product-requirements.md).
> **Principle:** *Data Ingestion ≠ Inference.* The Harvester never calls an agent.

### Workstream
1. **Pluggable harvester module** (`app/infrastructure/harvester/`) — auto-discovered plugin extractors (`yt-dlp`, `twscrape`, and contributable platform plugins). **Zero-hardcode:** all targets from `scraper_config.yaml`.
2. **Cron scheduling** — per-source `cadence`.
3. **3-layer anti-spam filter** — L1 heuristic → L2 text-clean → L3 batched LLM judge → dedupe + language detect.
4. **Raw Data Lake** — immutable, `tenant_id`-stamped landing zone (`texts/` raw, `filtered/` clean).

> **Data target (V5.0):** the harvester collects **product information + public
> comment samples** that feed the Comment Assistant — not "content-formula"
> videos. The plugin architecture and 3-layer filter are unchanged; only the
> *what we collect* changed.

### Definition of done
- `./nassistant.sh harvest` + `filter` produce `raw_data_lake/filtered/approved.json` from configured public sources, with no hardcoded URLs anywhere. **Met.**

---

## Phase 1 — Skeleton ✅ · CORE

FastAPI core, `/health`, Docker Compose (redis + qdrant + core-api), unified `cli.py`, Hexagonal layout (`domain`/`application`/`infrastructure`/`api`). **Met.**

---

## Phase 2 — Vector Memory ✅ · CORE

> **Goal:** turn approved chunks into a queryable multilingual memory.
- Chunking strategy → `BAAI/bge-m3` embedding (1024-dim) → Qdrant upsert with `{tenant_id, doc_id, source, locale, ingested_at}`.
- **Multi-namespace:** mandatory `tenant_id` payload filter on every `upsert`/`search`; cross-namespace query is a violation.
- **Learn:** code cosine similarity by hand; understand the embedding space; cross-lingual retrieval (VN query → DE docs).
- **DoD:** a `tenant_id`-filtered Qdrant query returns harvested chunks; cross-language isolation test passes.
- **Shipped:** `chunker.py`, `bge_embedder.py` (FlagEmbedding), `qdrant_store.py` (idempotent upsert + namespace-filtered search), `ingestion.py` (hexagonal DI). CLI commands `ingest` + `search`. Docker Compose profile `rag`.
- **Debt to carry into Phase 3:** cross-language isolation unit tests not yet written (DoD partially met).

---

## Phase 3 — Advanced RAG + Eval ⏳ · CORE

> **Goal:** a retrieval brain that grades and corrects itself — and that you can
> **measure**. Structured as a **3-stage pipeline** (Pre-Retrieval → Retrieval →
> Post-Retrieval) so each advanced technique is a **togglable node**, not a
> hardcoded step. Every technique is built **by hand** (pure Python over
> `LLMClientBase` + `qdrant-client`; LangGraph for flow only — §5 of the
> tech-stack rule) and **benchmarked on vs off** — *learning RAG without
> measuring is learning blind.*

### Retrieval core (the brain)
- **Hybrid Search** — dense (bge-m3) + sparse (BM25), fused with **Reciprocal Rank Fusion (RRF)** (code the RRF formula by hand). ✅ shipped: `BM25Index`, `HybridRetriever`. **Learn:** when dense beats sparse and vice-versa; the RRF math.
- **Cross-encoder reranking** — after fusion, re-score the top-k with **`bge-reranker-v2-m3`** (same family as bge-m3), which reads query+doc *together*. **Learn:** why reranking is the single biggest top-k quality lift after retrieval; **bi-encoder vs cross-encoder** trade-offs (latency vs precision).
- **Corrective RAG (CRAG)** — a LangGraph loop that scores retrieval relevance and self-corrects **in-store** (re-query / widen-`top_k` / relax threshold / BM25 fallback) before generation. Optional `web_search` correction is **off by default and disabled under `INFERENCE_MODE=self_hosted`** — no egress ([`ai-agent-design.md`](ai-agent-design.md) §8.6).
- **Domain adapter** — when a niche is selected, bias retrieval toward that niche's namespace + style.

### Pre-Retrieval — Query Transformation *(optional, per-query flag)*
- **Multi-Query** — one LLM call splits a complex question into 3–4 sub-queries; search all, fuse the results back through the **existing RRF** (no new fusion code).
- **HyDE** — generate a hypothetical answer and embed *that* (not the raw question), closing the query↔document vocab gap on deep niches.
- **Cost/latency:** each adds one local LLM call (~2–4 s on qwen2.5:3b). Expose as `query_transform: "none" | "multi_query" | "hyde"`. Run the transform **async** and **emit a status run-event** (log/WebSocket, per [`ai-agent-design.md`](ai-agent-design.md) §3.5). *No UI is built in this phase* — UI consumption is deferred to Phase 6's thin optional panel.

### Retrieval — chunking strategy
- **Semantic chunking** — split documents by **meaning** (embedding-distance / topic boundaries), not a fixed token length. **Learn:** how chunk granularity shapes retrieval quality; when semantic boundaries beat fixed windows.
- **Parent-Child (small-to-big)** — index **child** chunks (~200 tok) for precision; on a hit, fetch the wrapping **parent** block (~1000 tok) for context.
  - **Qdrant pattern (pure `qdrant-client`, no LangChain):** child payload `{doc_type: "child", parent_id, text}`; build a **payload index on `parent_id`**; after top-k children, dedupe their `parent_id`s and a second `scroll` / `search` with a `FieldCondition` filter pulls the parents in one call.
  - Ships as a **mode** (`chunk_strategy: "flat" | "semantic" | "parent_child"`), not a replacement for Phase 2's flat chunking — short social content (comment replies, product blurbs) can stay flat.

### Retrieval — Metadata filtering *(used live by the Comment Assistant)*
- Combine a **structured payload filter** (e.g. `product_id`, `price_band`, `category`, `locale`) with the vector search, so the engine narrows to the **right product / price range *before*** semantic ranking — not "closest vector wins". **Learn:** how to compose Qdrant `Filter` conditions with `search`; why pre-filtering is the difference between "an answer" and "the answer about *this* product".

### Post-Retrieval — Context Compression (LLM extractor node)
- After RRF/rerank, an extractor node trims top-k chunks to **only the sentences that answer the query** — not optional given qwen2.5:3b's ~4k context budget (top-5 chunks alone can near-fill it).
- Built on **`LLMClientBase`**, *not* LLMLingua — keep the stack lean, local, and learnable. LLMLingua is a Phase 6 advanced option.
- **Anti-hallucination guardrail:** the extractor prompt forbids rewriting — *copy sentences verbatim from the source, add nothing, rephrase nothing.* **Defensive fallback:** if an extracted sentence is not a substring of its source chunk, drop the extraction and keep the raw chunk.

### Evaluation — *pulled up from "much later" to now*
- **Basic eval lands in this phase, not Phase 6.** Build a fixed gold set (≈10–20 query→expected-answer pairs per active niche) and wire **RAGAS** — **faithfulness, answer relevancy, context precision/recall** — plus a couple of custom metrics (e.g. "right-product hit rate" for the Comment Assistant).
- **Purpose:** A/B every technique (rerank on/off, CRAG on/off, query-transform on/off) and **read whether it actually improves** retrieval/answer quality and at what latency cost.
- **Heavy MLOps stays in Phase 6** (LangFuse/Prometheus/Grafana, CI/CD retrain). Only the **basic eval (RAGAS + A/B comparison)** comes up here.

### Implementation philosophy
- **Flow / routing / self-correction → LangGraph.** **RAG logic (transform, chunk, retrieve, rerank, filter, compress) → pure Python + `LLMClientBase` + `qdrant-client`.** No LangChain retriever wrappers — they couple to LangChain's own doc-store abstraction and fight the hand-built Qdrant layer. Recorded in [`../rules/tech-stack-rule.md`](../rules/tech-stack-rule.md) §5.
- Every advanced technique is a **flag**, defaulting off, so a fork only pays for what its niche needs.

### Learn
- RRF math, **cross-encoder reranking** (bi- vs cross-encoder), graph workflows, retrieval correction.
- **Query↔document space mismatch** and why transformation (Multi-Query / HyDE) helps.
- **Chunking granularity trade-offs** (semantic vs fixed; small-to-big) — index precision vs context richness.
- **Metadata pre-filtering** combined with vector search.
- **Token-budget management** in a constrained local LLM.
- **RAG evaluation metrics** (RAGAS) and how to A/B techniques.

### DoD
- Gold eval set built (≈10–20 query→expected-answer pairs per active niche), with RAGAS wired.
- CRAG + rerank measurably reduce hallucination / improve top-k vs plain top-k **on that eval set**.
- Each advanced technique (rerank, Multi-Query, HyDE, semantic chunking, parent-child, metadata filter, compression) is **independently togglable** and **benchmarked on vs off** for latency + retrieval quality on the same set.

---

## Phase 4 — Fine-tuning ⏳ · CORE

> **Goal:** teach the model the house style + per-niche voice via LoRA.
- **LoRA** on `Qwen2.5-7B`. Multi-domain dataset: a shared **base** dataset + optional **per-niche** examples. Forkers can train their own niche adapter.
- **Embedding / domain fine-tuning** lives here too (same fine-tuning cluster) — adapt `bge-m3` to the niche's vocabulary when the gold-set eval from Phase 3 shows retrieval is the bottleneck. *Not* crammed into Phase 3.
- **Quantization / serving:** merge adapter → GGUF (Q4/Q5/Q8) → serve via Ollama.
- **Learn:** the low-rank update math (`ΔW = B·A`), rank `r` trade-offs, quantization, dataset & embedding-tuning design.
- **DoD:** before/after on a fixed test set shows ↑ JSON-output parse rate, ↑ style consistency, ↓ hallucination, and (if embedding-tuned) ↑ retrieval precision on the Phase 3 gold set.

---

## Phase 5 — Agentic Orchestrator & Comment Assistant ⏳ · CORE

> **Goal:** a Supervisor–Worker agent team that produces **reviewed**, grounded
> replies — the **Comment Assistant** end-to-end, with a human as the final gate.
- **LangGraph Supervisor–Worker:** Researcher → Creator → **Critic** (see [`ai-agent-design.md`](ai-agent-design.md)). The **Critic is the moat**: it blocks fabricated facts and unverified efficacy claims (critical for cosmetics/health).
- **Human-in-the-loop:** a Critic-passed draft goes to a **human review queue** to approve / edit / reject. **Nothing is auto-sent.** When an approved reply is sent, it uses the platform's **official API** — never browser automation.
- **Domain router:** user picks a niche → system switches retrieval namespace + prompt style.
- **Tool calling:** namespace-scoped RAG search, draft generation, review-queue handoff.
- **Learn:** multi-agent design, grounding & anti-hallucination, human-in-the-loop workflows, niche routing.

---

## Phase 6 — Production, MLOps & Evaluation ⏳ · CORE

> **Goal:** make it observable, evaluable, and reproducible at scale.
- **Full Docker stack:** Qdrant + Ollama + FastAPI + Redis queue.
- **Heavy evaluation & observability:** extend Phase 3's RAGAS into release-over-release tracking; LLM-as-Judge + small human eval; before/after fine-tuning comparison; logging (input/output, latency, token usage, retrieval score); monitoring (LangFuse / Prometheus + Grafana).
- **Config system:** `config.yaml` to pick model, niche, style without code changes.
- **Light MLOps:** version dataset / LoRA adapter / prompts (DVC or Git + HF Hub); experiment tracking (W&B free tier or MLflow local); simple CI/CD for retraining.
- **Optional thin UI:** Streamlit/Gradio review panel over the same local API.
- **Learn:** eval frameworks at scale, observability, reproducible ML.

---

## Phase 7 — Community & Extensibility ⏳ · CORE

> **Goal:** make forking trivial.
- **Niche templates:** seller-affiliate, beauty, tech, education… (config + dataset).
- **Plugin architecture:** easy to add a new scraper or LLM client.
- **Example projects:** e.g. "Stand up a Comment Assistant for your shop in an afternoon."
- **Docs:** how to train a LoRA for a new niche; how to add a custom scraper.

---

## ★ OPTIONAL Track — Visual & Character Engine 🧩 · needs GPU

> **Not on the main learning path.** This teaches diffusion/video, not the core
> AI-engineering route. The agent/plugin architecture lets you add it **later
> without breaking** what's built — it slots a Visual Director + Video Producer
> into the agent graph without changing existing roles' contracts.
- **Consistent character / avatar:** ComfyUI + IP-Adapter + FaceID + character LoRA.
- **Image generation:** Flux / SDXL + ControlNet (pose, outfit, product placement); the LLM emits structured `{visual_prompt, style, scene}` JSON.
- **Video pipeline:** image-to-video / text-to-video (local), lip-sync, TTS voice clone (XTTS / CosyVoice), ffmpeg auto-edit.
- **Honest caveat:** requires a real GPU; not realistically CPU-local.

---

## What you'll learn deeply (constant across phases)

- **Math:** embeddings, cosine similarity, RRF, **cross-encoder reranking**, low-rank adaptation, quantization, **RAG evaluation metrics**.
- **Architecture:** advanced RAG, agentic workflow (LangGraph), vector DB, multi-namespace, human-in-the-loop.
- **Production:** fine-tuning, quantization, pipeline orchestration, eval, light MLOps.
- **Engineering:** modular code, Docker, API design, open-source best practices.
- **Optional / Visual AI:** ComfyUI workflows, ControlNet, consistency techniques *(GPU track)*.

---

# 🌍 KẾ HOẠCH THỰC THI — Nyxara (V5.0, Bản Học tập · Hướng ngách)

> **Phạm vi:** lộ trình đầy đủ cho **một repo MIT duy nhất** `nyxara` — một **động
> cơ RAG đa ngôn ngữ + agentic, tự build từ đầu để học sâu**, hướng tới một ngách
> cụ thể: tự động hóa content & social cho **seller-affiliate trên TikTok Shop /
> Shopee (VN)**. Không có tầng thương mại, không có giai đoạn SaaS hóa.
> **Sản phẩm-lõi đầu tiên:** **Comment Assistant** — đọc comment công khai dưới
> video bán hàng → RAG truy xuất đúng thông tin sản phẩm → soạn câu trả lời đúng
> giọng → **người duyệt rồi mới gửi** (human-in-the-loop, không auto-đăng; khi
> gửi thì dùng **API chính thức** của nền tảng).
> `tenant_id` là một **namespace** để chứa nhiều niche/user trong một bản cài —
> không phải cách ly thanh toán. Không auth, không dashboard, không thu phí.

## Tổng quan các Chặng

| Chặng | Nhánh | Chủ đề | Trạng thái |
|---|---|---|---|
| **0. Nền móng** | CORE | Harvester: **dữ liệu sản phẩm + mẫu comment công khai**, repo MIT sạch, ví dụ theo niche | 🟢 Xong |
| **1. Khung xương** | CORE | FastAPI core, `/health`, Docker, CLI thống nhất | ✅ Xong |
| **2. Bộ nhớ Vector** | CORE | Chunking + `bge-m3` + Qdrant + đa namespace | ✅ Xong |
| **3. RAG Nâng cao + Eval** | CORE | Hybrid + RRF + **rerank** + CRAG + query-transform + parent-child + compression + **lọc metadata** + **semantic chunking**, tất cả bật/tắt theo query, kèm **eval RAGAS + A/B** | 🚧 Đang làm |
| **4. Fine-tuning** | CORE | LoRA trên Qwen2.5-7B, merge GGUF, dataset đa domain, **fine-tune embedding/domain** | ⏳ Dự kiến |
| **5. Agentic Orchestrator** | CORE | LangGraph Supervisor–Worker (Researcher → Creator → **Critic**), **Comment Assistant** end-to-end, **human-in-the-loop**, domain router | ⏳ Dự kiến |
| **6. Production, MLOps & Eval** | CORE | Full Docker stack, MLOps nặng (LangFuse/Prometheus/Grafana), CI/CD retrain, experiment tracking | ⏳ Dự kiến |
| **7. Cộng đồng & Mở rộng** | CORE | Template niche, kiến trúc plugin, dự án ví dụ | ⏳ Dự kiến |
| **★ Visual & Character Engine** | **OPTIONAL** | ComfyUI nhân vật nhất quán, SDXL/Flux + ControlNet, video + TTS + ffmpeg | 🧩 Add-on · cần GPU |

### Những thứ học sâu (xuyên suốt mọi chặng)
- **Toán học:** embedding, cosine similarity, RRF, **cross-encoder reranking**, low-rank adaptation (LoRA), lượng tử hóa, **các chỉ số đánh giá RAG**.
- **Kiến trúc:** RAG nâng cao, agentic workflow (LangGraph), vector DB, đa namespace, human-in-the-loop.
- **Production:** fine-tuning, lượng tử hóa, điều phối pipeline, eval, MLOps nhẹ.
- **Kỹ thuật:** code modular, Docker, thiết kế API, best practice mã nguồn mở.
- **Tùy chọn / Visual AI:** ComfyUI workflows, ControlNet, kỹ thuật nhất quán *(nhánh GPU)*.

> Chi tiết từng chặng xem bản tiếng Anh ở trên — nội dung tương ứng 1-1.
