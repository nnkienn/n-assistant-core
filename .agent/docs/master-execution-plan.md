# 🗺️ MASTER EXECUTION PLAN — N-Assistant Core (V4.0, Learning Edition)

> **Scope:** the full roadmap for the **single MIT repo** `n-assistant-core`. This
> is an open-source, modular **Virtual Content Factory** built as a learning
> vehicle — fork it for your niche, run it 100% local. There is no commercial
> layer and no SaaS productization stage.
> **Companion docs:** [`product-requirements.md`](product-requirements.md) ·
> [`ai-agent-design.md`](ai-agent-design.md) ·
> [`../rules/tech-stack-rule.md`](../rules/tech-stack-rule.md).

---

## Overall goal

A modular Virtual Content Factory anyone can fork and customize for their niche
(MMO, Game AI, Beauty, Crypto, Education…). Each phase is ordered to teach a
layer of the stack from scratch — the math, the architecture, and the
production craft — not just to ship features.

`tenant_id` is a **namespace** for hosting several niches/users in one install.
It is not customer-billing isolation. No auth, no dashboard, no monetization.

---

## Phase overview

| Phase | Theme | Status |
|---|---|---|
| **0. Foundation** | Data crawling pipeline (raw JSON from X, YouTube, web), clean MIT repo, per-niche examples | 🟢 Done |
| **1. Skeleton** | FastAPI core, `/health`, Docker, unified CLI | ✅ Done |
| **2. Vector Memory** | Chunking + `bge-m3` + Qdrant + multi-namespace | ✅ Done |
| **3. Advanced RAG** | Hybrid Search + RRF + Corrective RAG (CRAG) via LangGraph; per-niche domain adapter | 🚧 In progress |
| **4. Fine-tuning** | LoRA on Qwen2.5-7B, multi-domain dataset, GGUF merge | ⏳ Planned |
| **5. Visual & Character Engine** | ComfyUI consistent character, SDXL/Flux + ControlNet, video + TTS + ffmpeg | ⏳ Planned |
| **6. Agentic Orchestrator** | LangGraph multi-agent + domain router + tool calling | ⏳ Planned |
| **7. Production, MLOps & Eval** | Full Docker stack, RAGAS + custom metrics, monitoring, config.yaml, CI/CD, experiment tracking | ⏳ Planned |
| **8. Community & Extensibility** | Niche templates, plugin architecture, example projects | ⏳ Planned |

> **Deep-learning threads running through every phase:** embedding & similarity
> math, RRF, low-rank adaptation (LoRA), quantization, agentic graphs, ComfyUI
> consistency, evaluation, and light MLOps.

---

## Phase 0 — Foundation (Harvester) ✅

> **Goal:** an autonomous, scheduled subsystem that acquires **public** data and
> lands it — cleaned and `tenant_id`-tagged — ready for Qdrant, **without any LLM
> in the loop**. See [`product-requirements.md` §3.8](product-requirements.md).
> **Principle:** *Data Ingestion ≠ Inference.* The Harvester never calls an agent.

### Workstream
1. **Pluggable harvester module** (`app/infrastructure/harvester/`) — auto-discovered plugin extractors (Playwright + `playwright-stealth`, `yt-dlp`, `twscrape`). **Zero-hardcode:** all targets from `scraper_config.yaml`.
2. **Cron scheduling** — per-source `cadence`.
3. **3-layer anti-spam filter** — L1 heuristic → L2 text-clean → L3 batched LLM judge → dedupe + language detect.
4. **Raw Data Lake** — immutable, `tenant_id`-stamped landing zone (`texts/` raw, `filtered/` clean).

### Definition of done
- `./nassistant.sh harvest` + `filter` produce `raw_data_lake/filtered/approved.json` from configured public sources, with no hardcoded URLs anywhere. **Met.**

---

## Phase 1 — Skeleton ✅

FastAPI core, `/health`, Docker Compose (redis + qdrant + core-api), unified `cli.py`, Hexagonal layout (`domain`/`application`/`infrastructure`/`api`). **Met.**

---

## Phase 2 — Vector Memory ✅

> **Goal:** turn approved chunks into a queryable multilingual memory.
- Chunking strategy → `BAAI/bge-m3` embedding (1024-dim) → Qdrant upsert with `{tenant_id, doc_id, source, locale, ingested_at}`.
- **Multi-namespace:** mandatory `tenant_id` payload filter on every `upsert`/`search`; cross-namespace query is a violation.
- **Learn:** code cosine similarity by hand; understand the embedding space; cross-lingual retrieval (VN query → DE docs).
- **DoD:** a `tenant_id`-filtered Qdrant query returns harvested chunks; cross-language isolation test passes.
- **Shipped:** `chunker.py`, `bge_embedder.py` (FlagEmbedding), `qdrant_store.py` (idempotent upsert + namespace-filtered search), `ingestion.py` (hexagonal DI). CLI commands `ingest` + `search`. Docker Compose profile `rag`.
- **Debt to carry into Phase 3:** cross-language isolation unit tests not yet written (DoD partially met).

---

## Phase 3 — Advanced RAG ⏳

> **Goal:** a retrieval brain that grades and corrects itself.
- **Hybrid Search** — dense (bge-m3) + sparse (BM25), fused with **Reciprocal Rank Fusion (RRF)** (code the RRF formula by hand).
- **Corrective RAG (CRAG)** — a LangGraph loop that scores retrieval relevance and self-corrects (re-query / fallback) before generation.
- **Domain adapter** — when a niche is selected, bias retrieval toward that niche's namespace + style.
- **Learn:** RRF math, graph workflows, retrieval correction.
- **DoD:** CRAG measurably reduces hallucination vs plain top-k on a fixed eval set.

---

## Phase 4 — Fine-tuning ⏳

> **Goal:** teach the model the house style + per-niche voice via LoRA.
- **LoRA** on `Qwen2.5-7B`. Multi-domain dataset: a shared **base** dataset + optional **per-niche** examples (MMO, Game AI…). Forkers can train their own niche adapter.
- **Quantization / serving:** merge adapter → GGUF (Q4/Q5/Q8) → serve via Ollama.
- **Learn:** the low-rank update math (`ΔW = B·A`), rank `r` trade-offs, quantization.
- **DoD:** before/after on a fixed test set shows ↑ JSON-output parse rate, ↑ style consistency, ↓ hallucination.

---

## Phase 5 — Visual & Character Engine ⏳

> **Goal:** generate consistent visuals and video for any topic.
- **Consistent character / avatar:** ComfyUI + IP-Adapter + FaceID + character LoRA (forkers train their own KOL/game character).
- **Image generation:** Flux / SDXL + ControlNet (pose, outfit, product placement); the LLM emits structured `{visual_prompt, style, scene}` JSON.
- **Video pipeline:** image-to-video / text-to-video (local), lip-sync, TTS voice clone (XTTS / CosyVoice), ffmpeg auto-edit (subtitles, trend music, transitions).
- **Modular:** plugin system for visual workflows (e.g. Game-AI gameplay footage + AI-commentary overlay).
- **Learn:** consistency techniques, diffusion control, video assembly.

---

## Phase 6 — Agentic Orchestrator & Multi-Niche ⏳

> **Goal:** a full multi-agent content team with niche awareness.
- **LangGraph multi-agent:** Researcher → Script Writer → Visual Director → Video Producer → Critic (see [`ai-agent-design.md`](ai-agent-design.md)).
- **Domain router:** user picks a niche (e.g. "Game AI") → system switches retrieval namespace + prompt style + visual style.
- **Tool calling:** search web, generate image, run ffmpeg, export video.
- **Learn:** multi-agent design, routing, tool orchestration.

---

## Phase 7 — Production, MLOps & Evaluation ⏳

> **Goal:** make it observable, evaluable, and reproducible.
- **Full Docker stack:** Qdrant + Ollama + ComfyUI + FastAPI + Redis queue.
- **Evaluation:** RAGAS (faithfulness, relevance, answer correctness) + custom metrics for script quality, visual consistency, engagement proxy; LLM-as-Judge + small human eval. Before/after fine-tuning comparison.
- **Observability:** logging (input/output, latency, token usage, retrieval score), monitoring (LangFuse / Prometheus + Grafana), error handling & fallback.
- **Config system:** `config.yaml` to pick model, niche, character, output style without code changes.
- **Light MLOps:** version dataset / LoRA adapter / prompts (DVC or Git + HF Hub); experiment tracking (W&B free tier or MLflow local); simple CI/CD for retraining.
- **Learn:** eval frameworks, observability, reproducible ML.

---

## Phase 8 — Community & Extensibility ⏳

> **Goal:** make forking trivial.
- **Niche templates:** MMO Affiliate, Game AI, Tech, Education… (config + dataset).
- **Plugin architecture:** easy to add a new scraper, visual backend, or TTS.
- **Example projects:** e.g. "How to make Game-AI Shorts in 5 minutes."
- **Docs:** how to train a LoRA for a new niche, how to add a custom ComfyUI workflow.

---

## What you'll learn deeply (constant across phases)

- **Math:** embeddings, cosine similarity, RRF, low-rank adaptation, quantization.
- **Architecture:** advanced RAG, agentic workflow (LangGraph), vector DB, multi-namespace.
- **Production:** fine-tuning, quantization, pipeline orchestration, eval, light MLOps.
- **Visual AI:** ComfyUI workflows, ControlNet, consistency techniques.
- **Engineering:** modular code, Docker, API design, open-source best practices.

---

# 🌍 KẾ HOẠCH THỰC THI — N-Assistant Core (V4.0, Bản Học tập)

> **Phạm vi:** lộ trình đầy đủ cho **một repo MIT duy nhất** `n-assistant-core` —
> một **Nhà máy Nội dung Ảo** mã nguồn mở, modular, xây để **học sâu**. Fork cho
> niche của bạn, chạy 100% local. Không có tầng thương mại, không có giai đoạn
> SaaS hóa.
> `tenant_id` là một **namespace** để chứa nhiều niche/user trong một bản cài —
> không phải cách ly thanh toán. Không auth, không dashboard, không thu phí.

## Tổng quan các Chặng

| Chặng | Chủ đề | Trạng thái |
|---|---|---|
| **0. Nền móng** | Pipeline cào dữ liệu (JSON thô từ X, YouTube, web), repo MIT sạch, ví dụ theo niche | 🟢 Xong |
| **1. Khung xương** | FastAPI core, `/health`, Docker, CLI thống nhất | ✅ Xong |
| **2. Bộ nhớ Vector** | Chunking + `bge-m3` + Qdrant + đa namespace | 🚧 Đang làm |
| **3. RAG Nâng cao** | Hybrid Search + RRF + Corrective RAG (CRAG) qua LangGraph; domain adapter theo niche | ⏳ Tiếp theo |
| **4. Fine-tuning** | LoRA trên Qwen2.5-7B, dataset đa domain, merge GGUF | ⏳ Dự kiến |
| **5. Visual & Character Engine** | ComfyUI nhân vật nhất quán, SDXL/Flux + ControlNet, video + TTS + ffmpeg | ⏳ Dự kiến |
| **6. Agentic Orchestrator** | LangGraph multi-agent + domain router + tool calling | ⏳ Dự kiến |
| **7. Production, MLOps & Eval** | Full Docker stack, RAGAS + custom metrics, monitoring, config.yaml, CI/CD, experiment tracking | ⏳ Dự kiến |
| **8. Cộng đồng & Mở rộng** | Template niche, kiến trúc plugin, dự án ví dụ | ⏳ Dự kiến |

### Những thứ học sâu (xuyên suốt mọi chặng)
- **Toán học:** embedding, cosine similarity, RRF, low-rank adaptation (LoRA), lượng tử hóa.
- **Kiến trúc:** RAG nâng cao, agentic workflow (LangGraph), vector DB, đa namespace.
- **Production:** fine-tuning, lượng tử hóa, điều phối pipeline, eval, MLOps nhẹ.
- **Visual AI:** ComfyUI workflows, ControlNet, kỹ thuật nhất quán.
- **Kỹ thuật:** code modular, Docker, thiết kế API, best practice mã nguồn mở.

> Chi tiết từng chặng xem bản tiếng Anh ở trên — nội dung tương ứng 1-1.
