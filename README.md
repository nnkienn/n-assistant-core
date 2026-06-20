<div align="center">

# Nyxara 🤖🚀

### Learn AI engineering for real — build a multilingual RAG + agentic engine from scratch, aimed at one concrete niche

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)

**Most "learn AI" side projects die as glued-together tutorials with no users and no way to tell if anything works. Nyxara is the opposite bet: you build every layer yourself — advanced RAG, fine-tuning, agentic workflows, evaluation — and you point it at one real job: a *Comment Assistant* for TikTok Shop / Shopee seller-affiliates. Human-in-the-loop, never auto-post.**

🌐 🇬🇧 **English** · 🇻🇳 [Tiếng Việt](./README.vi.md) · 🇩🇪 [Deutsch](./README.de.md) · 🇨🇳 [中文](./README.zh.md)

</div>

---

## 🎯 Why this exists

Two things kill most "I'm learning AI engineering" projects:

1. **They're stitched from tutorials.** You wire up a LangChain retriever, get an answer, and never learn *why* dense retrieval missed, what RRF actually computes, or whether your reranker helped. The understanding never lands.
2. **They have no destination.** No real task, no real user, no way to measure "better." Motivation evaporates.

**Nyxara fixes both.** It is a multilingual **RAG + agentic engine you build from scratch** — owning the embedding math, the RRF formula, the cross-encoder rerank, the LoRA update, the eval metrics — and it is pointed at a **concrete niche with real (if small) users:** content & social automation for **seller-affiliates on TikTok Shop / Shopee in Vietnam.**

> **For the reader:** if you want to *understand* AI engineering — not just call an API — by building one coherent system with a real goal you can demo and measure, this repo is for you. It is a **learning vehicle first**, a niche tool second. Not a multi-tenant SaaS, not a market play.

It runs **100% local** by default (no byte leaves your box unless you choose a cloud tier), and a `tenant_id` **namespace** lets one install host several niches side by side — *folder per niche*, not *tenant per paying customer*. No billing, no auth, no dashboard.

---

## 🛍️ Flagship use case — the Comment Assistant

This is the niche destination that gives every technique a reason to exist.

A seller-affiliate posts a product video on TikTok Shop / Shopee. Underneath, dozens of comments pile up: *"giá bao nhiêu?"*, *"da dầu dùng được không?"*, *"ship mấy ngày?"*. The Comment Assistant turns that firehose into reviewed, on-brand replies:

1. **Read** the public comments under the video.
2. **Retrieve** the right product facts — price, ingredients, usage, official link — **filtered to *that specific product*** (metadata filter first, *then* semantic search — not "closest vector wins").
3. **Draft** a reply in the seller's voice and locale.
4. **Critique** it: a dedicated **Critic agent blocks fabricated facts and unverified efficacy claims** — non-negotiable for cosmetics/health, where a wrong claim is a trust and legal problem.
5. **Human approves** before anything is sent. **Nyxara never auto-posts.** When a reply *is* sent, it goes through the platform's **official API** — never a stealth browser.

Every RAG/agent/eval technique below earns its place by answering a real question here: *did retrieval pull the right product? did rerank actually lift the answer? did the Critic catch the false claim?*

---

## 🔥 Core Capabilities

### 1. 🌾 Pluggable Harvester — Any Platform, Community-Driven
**This is Phase 0 — the foundation everything else feeds on.** A scheduled (cron) crawler acquires **public** data — **product information and public comment samples** for the Comment Assistant — stamps it with a `tenant_id` namespace, lands it in a per-niche **Raw Data Lake**, then cleans it through a 3-layer anti-spam filter — fully decoupled from the agents (*Data Ingestion ≠ Inference*; this layer **never** calls an LLM).

**Plug in any platform — drop one file.** The engine auto-discovers every plugin under [`extractors/plugins/`](./app/infrastructure/harvester/extractors/plugins/) at runtime. A new source is one class — no core changes, no hardcoded imports:

```python
class MyPlatformExtractor(BaseExtractor):
    PLUGIN_TYPE = "my_platform"          # ← referenced by `type:` in scraper_config.yaml
    async def extract(self) -> list[HarvestedItem]:
        url = self.options["url"]        # everything from YAML — zero-hardcode
        ...
```

A crashing plugin is logged and skipped — one bad source never takes the whole run down.

**Shipped today:** `x_twscrape` (X / Twitter via twscrape) · `youtube_shorts` (YouTube Shorts via yt-dlp).
**We need your help** 🤝 — public sites change their markup and rate limits constantly. Contribute a new platform plugin (TikTok, Shopee, Instagram, Reddit…) or help keep an existing extractor **resilient and ToS-compliant**. The whole contract is one file: [`base.py`](./app/infrastructure/harvester/extractors/base.py).

**3-layer anti-spam filter** — fail-fast and cost-aware; each item must earn the next layer, so the paid LLM call only ever sees what already survived two free CPU gates:

| Layer | Stage | Cost | Drops |
|---|---|---|---|
| **L1** | Heuristic (hashtag / word-count / mention gates) | O(1) CPU | engagement-bait, one-liners, mass-mention spam |
| **L2** | Text-clean (strip URLs, emojis, boilerplate) | O(n) CPU | items empty after cleaning |
| **L3** | LLM judge (batched, OpenAI-compatible) | ~1 API call / 10 items | jokes, replies, low-value chatter |

Approved items land in `raw_data_lake/filtered/approved.json`, Qdrant-ready. Sources and thresholds live in [`scraper_config.yaml`](./scraper_config.yaml) → `filter_config`, **never hardcoded**.

### 2. 🔀 Dual-Engine LLM Router (Local + Cloud)
A single `LLMClientBase` (OpenAI-compatible) interface lets every agent run on either engine **without a code change**:
- **Local / Dev tier:** Ollama or Apple MLX serving `Qwen2.5` / `Llama-3.1-8B-Instruct` → zero-cost R&D, fully offline.
- **Scale tier:** vLLM on a rented GPU (RunPod, AWS) or a fallback to a cloud API for heavy batches.

Routing is a **runtime config decision**, never a rewrite. The same agent code runs in both tiers.

> **Hardware expectations (honest):** the CORE phases run comfortably on a CPU/no-GPU box with a local 3B model. But the **Critic / CRAG grading** wants a capable model — on a 3B-only box that judging is *best-effort*, so route Tier-1 to a cloud/hybrid engine if you need strong anti-hallucination. The **OPTIONAL Visual Engine (ComfyUI image/video + TTS) needs a real GPU** and is not realistically CPU-local. "100% local" holds end-to-end on a GPU box; on CPU-only hardware it covers the RAG/agent brain, not the optional visual track.

### 3. 🧠 Multi-Niche & Multilingual RAG
- **Vector store:** [Qdrant](https://qdrant.tech/) with namespace-scoped collections.
- **Embeddings:** `BAAI/bge-m3` (1024-dim, 100+ languages) → one shared cross-lingual index, **no per-language collection**.
- **Namespace isolation:** every `upsert` / `search` carries a mandatory `tenant_id` payload filter, so multiple niches coexist in one store with **zero cross-niche bleed** — an architectural guarantee, not a runtime check.
- **Cross-language retrieval:** a Vietnamese niche can query its German-language knowledge base in one space.
- **What you learn here:** chunking strategy, the embedding math, cosine similarity by hand, then the full **Phase 3 advanced-RAG stack** — Hybrid Search, RRF, cross-encoder reranking, CRAG, query transformation, and measured evaluation (see the roadmap below).

### 4. 🕹️ Supervisor–Worker Agent Topology
We do **not** stuff everything into one giant prompt. Each request is decomposed into specialized roles:

| Role | Responsibility | Tools |
|---|---|---|
| **Supervisor (Planner)** | Decompose intent → ordered task graph; route to workers | Task router |
| **Researcher** | Namespace-scoped RAG query (drives the Phase 3 pipeline) | `search_vector_db(tenant_id, …)` |
| **Creator** | Draft the reply / copy in the seller's voice | `generate_text` |
| **Critic** | Anti-hallucination: block fabricated facts & unverified efficacy claims | RAG verifier (≤ 3 retry loops) |
| **Human Reviewer** | Approve / edit / reject before anything is sent — **the loop closes on a person, not on auto-send** | Review queue |

The **Critic is the moat**: it verifies grounding before a draft reaches the human, and the human is the final gate. **There is no auto-publish agent.** When an approved reply is sent, it goes through the platform's **official API**.

> The agent graph is plugin-shaped: the OPTIONAL Visual track (Phase later) can add a **Visual Director** and **Video Producer** node without changing the existing roles' contracts.

---

## 🏗️ Hexagonal Architecture

The domain core depends on nothing; the outside world plugs in through ports. You can replace Qdrant, the LLM engine, or the web framework without touching business logic.

```
n-assistant-core/
├── app/
│   ├── domain/                  # Pure business entities & ports — zero framework deps
│   ├── application/             # Use cases + filter pipelines (3-layer anti-spam)
│   ├── infrastructure/
│   │   └── harvester/           # engine.py · extractors/plugins/ (X, YouTube…) · filters/
│   └── api/                     # Driving adapter: FastAPI routers, schemas, DI wiring
├── cli.py                       # ★ Unified CLI — single entry point for all harvest ops
├── scraper_config.yaml          # Harvester sources + filter thresholds — zero-hardcode
├── raw_data_lake/               # Per-namespace landing zone: texts/ (raw) + filtered/ (clean)
├── docker-compose.yml           # redis + qdrant + core-api (+ harvester profile)
├── Dockerfile · Dockerfile.harvester   # core-API image · Chromium image for plugins
├── requirements.txt
└── LICENSE                      # MIT
```

---

## ⚡ Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.11) · Pydantic v2 · SQLAlchemy 2.x |
| Vector / RAG | **Qdrant** · `BAAI/bge-m3` embeddings (1024-dim, multilingual) · Hybrid + RRF + **cross-encoder rerank (`bge-reranker-v2-m3`)** + CRAG · metadata filtering · semantic chunking |
| Inference | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud API (scale) |
| Fine-tuning | LoRA on `Qwen2.5-7B` · GGUF quantization (Q4/Q5/Q8) merge · embedding/domain fine-tuning |
| Agent framework | LangGraph (Supervisor–Worker, multi-agent, human-in-the-loop) |
| Eval | **RAGAS** (faithfulness, answer relevancy, context precision/recall) + custom metrics + A/B toggling — **from Phase 3** |
| Async jobs | Celery 5 + Redis 7 broker |
| MLOps (Phase 6) | LangFuse / Prometheus + Grafana · DVC / W&B / MLflow (light) · CI/CD retrain |
| Visual / Video — *OPTIONAL* | ComfyUI · Flux / SDXL · ControlNet · IP-Adapter / FaceID · XTTS / CosyVoice · ffmpeg *(needs GPU)* |
| ML runtime | PyTorch (MPS on Mac, CUDA on Linux GPU) |
| Containers | Docker Compose (profiles: default, harvester, rag) |
| License | MIT |

---

## 🗺️ Roadmap — A Learning Path

The phases are ordered so each one teaches a layer of the stack from scratch. Status is honest, not aspirational. **CORE** phases are the main learning path; the **OPTIONAL** Visual track sits off to the side — the architecture lets you bolt it on later *without* breaking what's built, but it teaches diffusion/video, not the core AI-engineering route.

| Phase | Track | Theme | What you build & learn | Status |
|---|---|---|---|---|
| **0. Foundation** | CORE | Harvester: **product data + public comment samples** · clean MIT repo · per-niche examples | Plugin architecture, zero-hardcode config, 3-layer filter | 🟢 Done |
| **1. Skeleton** | CORE | FastAPI core, `/health`, Docker, unified CLI | Hexagonal architecture, container workflow | ✅ Done |
| **2. Vector Memory** | CORE | Chunking + `bge-m3` + Qdrant + multi-namespace | Embedding math, cosine similarity **by hand**, namespace isolation | ✅ Done |
| **3. Advanced RAG + Eval** | CORE | The full retrieval brain — **see the deep-dive table below** — plus measured evaluation (RAGAS + A/B) baked in | RRF & rerank math, query↔doc space, chunk granularity, token budgeting, graph workflows, *measuring whether each technique helps* | ⏳ In progress |
| **4. Fine-tuning** | CORE | **LoRA** on `Qwen2.5-7B` · GGUF merge · multi-domain dataset · **embedding/domain fine-tuning** | Low-rank update math, quantization, dataset & embedding-tuning design | ⏳ Planned |
| **5. Agentic Orchestrator** | CORE | LangGraph Supervisor–Worker (Researcher → Creator → **Critic**) · **Comment Assistant** end-to-end · **human-in-the-loop review** · domain router | Multi-agent design, grounding & anti-hallucination, HITL workflows, niche routing | ⏳ Planned |
| **6. Production, MLOps & Eval** | CORE | Full Docker stack · monitoring/logging (LangFuse, Prometheus + Grafana) · `config.yaml` · CI/CD retrain · experiment tracking (W&B / MLflow) · versioning (DVC / HF Hub) | Observability, reproducible ML, heavy MLOps | ⏳ Planned |
| **7. Community & Extensibility** | CORE | Niche templates (seller-affiliate, beauty, tech…) · plugin architecture (scraper / LLM client) · example projects | Open-source extensibility, plugin design | ⏳ Planned |
| **★ Visual & Character Engine** | **OPTIONAL** | ComfyUI + IP-Adapter / FaceID + character LoRA · Flux/SDXL + ControlNet · image/text→video · lip-sync + TTS clone (XTTS/CosyVoice) · ffmpeg auto-edit | Consistency techniques, diffusion control, video pipeline | 🧩 Add-on · needs GPU |

### Phase 3 in depth — Advanced RAG, every technique togglable per query

The whole point of Phase 3 is to build each technique **by hand** (pure Python over `LLMClientBase` + `qdrant-client`, LangGraph for flow only) and then **measure whether it actually helps** — *learning RAG without measuring is learning blind.*

| Technique | What it does | What you learn |
|---|---|---|
| **Hybrid Search** (dense + sparse/BM25) | run semantic + keyword retrieval together | when dense beats sparse and when sparse beats dense |
| **RRF** (Reciprocal Rank Fusion) | merge several ranked lists into one | the RRF formula by hand; how to fuse rankings |
| **Cross-encoder reranking** (`bge-reranker-v2-m3`, same family as bge-m3) | re-score the top-k by reading query+doc *together* | why reranking lifts top-k quality the most after retrieval; **bi-encoder vs cross-encoder** |
| **CRAG** (Corrective RAG) via LangGraph | grade retrieved context, then retry / widen / escalate | self-scoring context; self-correcting retrieval loops |
| **Query Transformation** (Multi-Query + HyDE) | expand / rewrite the query before search | the query↔document space mismatch and how to close it |
| **Parent-Child** (small-to-big) retrieval | match on small chunks, return the big parent block | precise match *and* full context; chunk granularity |
| **Context Compression** | trim retrieved chunks to only the answering sentences | cutting noise; token-budget management on a small local LLM |
| **Metadata filtering** (vector + filter) | filter to the right product / price band *before* semantic search | combining structured filter + vector search — **used live in the Comment Assistant** |
| **Semantic chunking** | split by meaning, not fixed length | how chunk granularity shapes retrieval quality |
| **Evaluation** (RAGAS + custom + A/B) | faithfulness, answer relevancy, context precision/recall | **whether rerank / CRAG / rewrite truly improve** — pulled up from "much later" to *now* |

Every technique is a **per-query flag**, default off, so you can A/B *with* vs *without* and read the metrics. Heavy MLOps (LangFuse/Prometheus/Grafana, CI/CD retrain) stays in Phase 6 — only the **basic eval (RAGAS + A/B comparison)** comes up to Phase 3.

### What you'll learn deeply
- **Math:** embeddings, cosine similarity, RRF, **cross-encoder reranking**, low-rank adaptation (LoRA), quantization, **RAG evaluation metrics**.
- **Architecture:** advanced RAG, agentic workflows (LangGraph), vector DB, multi-namespace, human-in-the-loop.
- **Production:** fine-tuning, quantization, pipeline orchestration, evaluation, light MLOps.
- **Engineering:** modular code, Docker, API design, open-source best practices.
- **Optional / Visual AI:** ComfyUI workflows, ControlNet, character/identity consistency *(if you add the optional track on a GPU box)*.

---

## 🚀 Quick Start

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # spins up redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

That's it — a full local AI engine on `http://localhost:8000`.

| Service | URL |
|---|---|
| Core API (RAG / LLM) | http://localhost:8000 |
| Qdrant (vector DB) | http://localhost:6333 |
| Redis (broker) | localhost:6379 |

📖 **[docs/HARVESTER_GUIDE.md](./docs/HARVESTER_GUIDE.md)** — Phase 0 deep-dive: plugin architecture, CLI reference, how to add a new scraper in 30 minutes.

**Run the data pipeline** — harvest then filter, **entirely through Docker** (no local Python, no venv). A thin wrapper runs the unified `cli.py` *inside* the harvester container:

```bash
# Linux / macOS: ./nassistant.sh <command>      Windows: .\nassistant.ps1 <command>

# Show all registered plugins + their on/off status in config/scraper_config.yaml
./nassistant.sh list-plugins

# Harvest: scrape every enabled source → Raw Data Lake
./nassistant.sh harvest

# Harvest a single named source (dry-run first to preview)
./nassistant.sh harvest --source product-catalog-demo --dry-run
./nassistant.sh harvest --source product-catalog-demo

# Harvest all sources of one plugin type, capping items at 5 each
./nassistant.sh harvest --type youtube_shorts --limit 5

# Filter: run the 3-layer anti-spam pipeline over all harvested data
./nassistant.sh filter

# Filter only one plugin type
./nassistant.sh filter --type youtube_shorts
```

Run `./nassistant.sh --help` or `./nassistant.sh <command> --help` to see all options.

> **Layer 3 calls an LLM**, so set `INFERENCE_PROVIDER` / `INFERENCE_BASE_URL` / `INFERENCE_MODEL` / `INFERENCE_API_KEY` in `.env` first — Gemini, OpenAI, or local Ollama (any OpenAI-compatible endpoint). Layers 1–2 are CPU-only and run without a key.

<details>
<summary>Prefer raw <code>docker compose</code>? (no wrapper)</summary>

The wrapper is just a one-liner around `docker compose run`. The harvester image ships `cli.py`, so any subcommand works:

```bash
docker compose --profile harvester run --rm harvester python cli.py list-plugins
docker compose --profile harvester run --rm harvester python cli.py harvest
docker compose --profile harvester run --rm harvester python cli.py filter
```

</details>

---

## 🔐 Non-Negotiable Engineering Rules

These are **constitutional**. PRs that violate them are auto-rejected.

- 🛡️ **Namespace everywhere.** Every Vector DB op, cache key, and audit log MUST carry a `tenant_id` namespace so niches never bleed into each other.
- 🧠 **Single embedding model.** `BAAI/bge-m3` is the only embedding allowed — no per-language model, no OpenAI ada.
- 🔌 **`LLMClientBase` abstraction.** Agents call `client.complete(...)` — never `openai.ChatCompletion.*` or `transformers` directly.
- ✅ **TDD mandatory.** Red → Green → Refactor. RAG/Agent logic needs **cross-language tests** (VN, EN, DE, CN).
- 🙋 **Human-in-the-loop, no auto-publish.** Drafts go to a person to approve, edit, or reject. Nothing is sent autonomously; when content *is* sent, it uses the platform's **official API** — never browser automation / stealth posting.
- 🌾 **Zero-hardcode harvesting.** Scraping targets live in `scraper_config.yaml`, public pages only, robots.txt respected.

---

<div align="center">

**License:** [MIT](LICENSE) · Free to use, fork, modify, and self-host. Built for the open-source AI community. 🌍

📞 **nnkienn@gmail.com**

</div>
