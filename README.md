<div align="center">

# N-Assistant Core 🤖🚀

### The Open-Source Virtual Content Factory — fork it for your niche, run it 100% local

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)

**A modular, MIT-licensed engine for building an autonomous AI content pipeline — harvest → remember → reason → fine-tune → generate visuals → publish. Runs fully local, no vendor lock-in.**

🌐 🇬🇧 **English** · 🇻🇳 [Tiếng Việt](./README.vi.md) · 🇩🇪 [Deutsch](./README.de.md) · 🇨🇳 [中文](./README.zh.md)

</div>

---

## 🎯 Project Vision

**N-Assistant Core** is an open-source **Virtual Content Factory**: a modular AI engine you **fork and customize for your own niche** — MMO/affiliate, Game AI, Beauty, Crypto, Education, anything — and run **100% locally**.

It chains a **multilingual Retrieval-Augmented Generation (RAG)** brain with a **LangGraph** agent graph and a **Playwright** automation arm, so an autonomous pipeline can **research → write → generate visuals → review → publish** content on YouTube, Facebook & Instagram — without a human in the loop, and without sending a single byte to a third-party cloud unless *you* choose to.

It is built as a **deep-learning vehicle, not a product to sell.** The goal is to *understand* every layer — the embedding math, RRF, LoRA low-rank updates, quantization, agentic graphs, ComfyUI consistency — by building it from scratch and owning every line that runs.

> **Multi-niche, not multi-tenant SaaS.** One install can host several niches side by side. A `tenant_id` (namespace) keeps each niche's knowledge separated in the vector store — your MMO index never bleeds into your Game AI one. There is **no billing, no auth, no commercial cloud** — just a clean namespace so you (or a fork) can run many domains from one engine.

---

## 🔥 Core Capabilities

### 1. 🌾 Pluggable Harvester — Any Platform, Community-Driven
**This is Phase 0 — the foundation everything else feeds on.** A scheduled (cron) crawler acquires **public** data, stamps it with a `tenant_id` namespace, lands it in a per-niche **Raw Data Lake**, then cleans it through a 3-layer anti-spam filter — fully decoupled from the agents (*Data Ingestion ≠ Inference*; this layer **never** calls an LLM).

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
**We need your help** 🤝 — platforms evolve their anti-bot defenses constantly. Contribute a new platform plugin (TikTok, Instagram, Reddit, LinkedIn…) or a fresh **bypass / stealth technique** for an existing one. The whole contract is one file: [`base.py`](./app/infrastructure/harvester/extractors/base.py).

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

### 3. 🧠 Multi-Niche & Multilingual RAG
- **Vector store:** [Qdrant](https://qdrant.tech/) with namespace-scoped collections.
- **Embeddings:** `BAAI/bge-m3` (1024-dim, 100+ languages) → one shared cross-lingual index, **no per-language collection**.
- **Namespace isolation:** every `upsert` / `search` carries a mandatory `tenant_id` payload filter, so multiple niches/users coexist in one store with **zero cross-niche bleed** — an architectural guarantee, not a runtime check.
- **Cross-language retrieval:** a Vietnamese niche can query its German-language knowledge base in one space.
- **What you learn here:** chunking strategy, the embedding math, cosine similarity by hand, then **Hybrid Search + RRF + Corrective RAG (CRAG)** as the brain matures (Phase 3).

### 4. 🕹️ Supervisor–Worker Agent Topology
We do **not** stuff everything into one giant prompt. Each request is decomposed into specialized roles:

| Role | Responsibility | Tools |
|---|---|---|
| **Supervisor (Planner)** | Decompose intent → ordered task graph; route to workers | Task router |
| **Researcher** | Trend-mine + namespace-scoped RAG query | `search_vector_db(tenant_id, …)` |
| **Creator** | Draft script / copy / storyboard | `generate_text`, `generate_image`, `generate_audio` |
| **Critic** | Voice review + claim-vs-context anti-hallucination | RAG verifier (≤ 3 retry loops) |
| **Publisher** | Trigger Playwright auto-upload | `publish_to_platform(tenant_id, …)` |

The Critic verifies grounding before anything ships. As the **Visual Engine** lands (Phase 5–6), this graph grows a **Visual Director** and **Video Producer**.

### 5. 📡 Omnichannel Auto-Distribution
**Redis + Celery** drain async jobs to **Playwright** headless browsers that publish while mimicking human behavior to stay within platform limits:
- YouTube Shorts · Facebook · Instagram Reels.
- Session cookies stored **AES-256 encrypted** (never plain-text).
- `playwright-stealth` to evade bot-detection.
- Schedule by namespace timezone + peak-hour heuristic.

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
| Vector / RAG | **Qdrant** · `BAAI/bge-m3` embeddings (1024-dim, multilingual) · Hybrid + RRF + CRAG |
| Inference | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud API (scale) |
| Fine-tuning | LoRA on `Qwen2.5-7B` · GGUF quantization (Q4/Q5/Q8) merge |
| Visual / Video | ComfyUI · Flux / SDXL · ControlNet · IP-Adapter / FaceID · XTTS / CosyVoice · ffmpeg |
| Agent framework | LangGraph (Supervisor–Worker, multi-agent) |
| Async jobs | Celery 5 + Redis 7 broker |
| Automation | Playwright + `playwright-stealth` |
| Eval / MLOps | RAGAS + custom metrics · LangFuse / Prometheus + Grafana · DVC / W&B / MLflow (light) |
| ML runtime | PyTorch (MPS on Mac, CUDA on Linux GPU) |
| Containers | Docker Compose (profiles: default, harvester, rag) |
| License | MIT |

---

## 🗺️ Roadmap — A Learning Path, Phases 0→8

The phases are ordered so each one teaches a layer of the stack from scratch. Status is honest, not aspirational.

| Phase | Theme | What you build & learn | Status |
|---|---|---|---|
| **0. Foundation** | Data crawling pipeline (raw JSON from X, YouTube, web) · clean MIT repo · per-niche examples | Plugin architecture, zero-hardcode config, 3-layer filter | 🟢 Done |
| **1. Skeleton** | FastAPI core, `/health`, Docker, unified CLI | Hexagonal architecture, container workflow | ✅ Done |
| **2. Vector Memory** | Chunking + `bge-m3` + Qdrant + multi-namespace | Embedding math, cosine similarity **by hand**, namespace isolation | ✅ Done |
| **3. Advanced RAG** | Hybrid Search + **RRF** + **Corrective RAG (CRAG)** via LangGraph · per-niche domain adapter | RRF math, graph workflows, retrieval correction | ⏳ Next |
| **4. Fine-tuning** | **LoRA** on `Qwen2.5-7B` · multi-domain dataset (base + per-niche) · GGUF merge | Low-rank update math, quantization, dataset design | ⏳ Planned |
| **5. Visual & Character Engine** | ComfyUI + IP-Adapter / FaceID + character LoRA · Flux/SDXL + ControlNet · image/text→video · lip-sync + TTS clone (XTTS/CosyVoice) · ffmpeg auto-edit | Consistency techniques, diffusion control, video pipeline | ⏳ Planned |
| **6. Agentic Orchestrator** | LangGraph multi-agent (Researcher → Script Writer → Visual Director → Video Producer → Critic) · **domain router** · tool calling | Multi-agent design, niche routing | ⏳ Planned |
| **7. Production, MLOps & Eval** | Full Docker stack (Qdrant + Ollama + ComfyUI + FastAPI + Redis) · **RAGAS** + custom metrics · monitoring/logging (LangFuse, Prometheus + Grafana) · `config.yaml` · CI/CD retrain · experiment tracking (W&B / MLflow) · dataset/adapter/prompt versioning (DVC / HF Hub) | Eval frameworks, observability, light MLOps | ⏳ Planned |
| **8. Community & Extensibility** | Niche templates (MMO, Game AI, Tech, Education…) · plugin architecture (scraper / visual / TTS) · example projects | Open-source extensibility, plugin design | ⏳ Planned |

### What you'll learn deeply
- **Math:** embeddings, cosine similarity, RRF, low-rank adaptation (LoRA), quantization.
- **Architecture:** advanced RAG, agentic workflows (LangGraph), vector DB, multi-namespace.
- **Production:** fine-tuning, quantization, pipeline orchestration, evaluation, light MLOps.
- **Visual AI:** ComfyUI workflows, ControlNet, character/identity consistency.
- **Engineering:** modular code, Docker, API design, open-source best practices.

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
./nassistant.sh harvest --source yt-long-matt-wolfe --dry-run
./nassistant.sh harvest --source yt-long-matt-wolfe

# Harvest all sources of one plugin type, capping items at 5 each
./nassistant.sh harvest --type youtube_long --limit 5

# Filter: run the 3-layer anti-spam pipeline over all harvested data
./nassistant.sh filter

# Filter only YouTube Long Video segments
./nassistant.sh filter --type youtube_long
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

- 🛡️ **Namespace everywhere.** Every Vector DB op, cache key, and audit log MUST carry a `tenant_id` namespace so niches/users never bleed into each other.
- 🧠 **Single embedding model.** `BAAI/bge-m3` is the only embedding allowed — no per-language model, no OpenAI ada.
- 🔌 **`LLMClientBase` abstraction.** Agents call `client.complete(...)` — never `openai.ChatCompletion.*` or `transformers` directly.
- ✅ **TDD mandatory.** Red → Green → Refactor. RAG/Agent logic needs **cross-language tests** (VN, EN, DE, CN).
- 🔒 **Encrypted session vault.** Playwright cookies → AES-256 → storage. Never plain-text.
- 🌾 **Zero-hardcode harvesting.** Scraping targets live in `scraper_config.yaml`, public pages only, robots.txt respected.

---

<div align="center">

**License:** [MIT](LICENSE) · Free to use, fork, modify, and self-host. Built for the open-source AI community. 🌍

📞 **nnkienn@gmail.com**

</div>
