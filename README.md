<div align="center">

# N-Assistant Core 🤖🚀

### The Autonomous Omnichannel AI Marketing Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)

**The MIT-licensed AI inference engine behind N Assistant — runs fully local, no vendor lock-in.**

🌐 🇬🇧 **English** · 🇻🇳 [Tiếng Việt](./README.vi.md) · 🇩🇪 [Deutsch](./README.de.md) · 🇨🇳 [中文](./README.zh.md)

</div>

---

## 🎯 Project Vision

**N-Assistant Core** is a multi-agent AI inference engine engineered to run **100% locally**.

It fuses a **multi-tenant, multilingual Retrieval-Augmented Generation (RAG)** brain with a **Playwright**-driven automation arm, so autonomous agents can **research → create → review → publish** content across YouTube, Facebook & Instagram — without a human in the loop, and without sending a single byte to a third-party cloud unless *you* choose to.

It is built for AI and DevOps engineers who want full control: swap the LLM, own the vector index, self-host the entire stack, and read every line of code that runs it.

---

## 🔥 Core Capabilities

### 1. 🌾 Pluggable Harvester — Any Platform, Community-Driven
**This is Phase 0 — the foundation everything else feeds on.** A scheduled (cron) crawler acquires **public** data, stamps it with `tenant_id`, lands it in a per-tenant **Raw Data Lake**, then cleans it through a 3-layer anti-spam filter — fully decoupled from the agents (*Data Ingestion ≠ Inference*; this layer **never** calls an LLM).

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
- **Local / Dev tier:** Ollama or Apple MLX serving `Llama-3.1-8B-Instruct` / `Qwen2.5` → zero-cost R&D, fully offline.
- **Production / Scale tier:** vLLM on rented GPU (RunPod, AWS) or a fallback to OpenAI / Claude for peak demand.

Routing is a **runtime config decision**, never a rewrite. The same agent code runs in both tiers.

### 3. 🧠 Multi-Tenant & Multilingual RAG
- **Vector store:** [Qdrant](https://qdrant.tech/) with tenant-scoped collections.
- **Embeddings:** `BAAI/bge-m3` (1024-dim, 100+ languages) → one shared cross-lingual index, **no per-language collection**.
- **Isolation:** every `upsert` / `search` enforces a mandatory `tenant_id` payload filter. **Zero cross-tenant leakage** is an architectural guarantee, not a runtime check.
- **Cross-language retrieval:** a Vietnamese tenant can query their German-language knowledge base in one space.

### 4. 🕹️ Supervisor–Worker Agent Topology
We do **not** stuff everything into one giant prompt. Each request is decomposed into specialized roles:

| Role | Responsibility | Tools |
|---|---|---|
| **Supervisor (Planner)** | Decompose intent → ordered task graph; route to workers | Task router |
| **Researcher** | Trend-mine + tenant-scoped RAG query | `search_vector_db(tenant_id, …)` |
| **Creator** | Draft script / copy / storyboard | `generate_text`, `generate_image`, `generate_audio` |
| **Critic** | Brand-voice review + claim-vs-context anti-hallucination | RAG verifier (≤ 3 retry loops) |
| **Publisher** | Trigger Playwright auto-upload | `publish_to_platform(tenant_id, …)` |

The Critic verifies grounding before anything ships.

### 5. 📡 Omnichannel Auto-Distribution
**Redis + Celery** drain async jobs to **Playwright** headless browsers that publish while mimicking human behavior to stay within platform limits:
- YouTube Shorts · Facebook · Instagram Reels.
- Session cookies stored **AES-256 encrypted** (never plain-text).
- `playwright-stealth` to evade bot-detection.
- Schedule by tenant timezone + peak-hour heuristic.

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
├── raw_data_lake/               # Per-tenant landing zone: texts/ (raw) + filtered/ (clean)
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
| Vector / RAG | **Qdrant** · `BAAI/bge-m3` embeddings (1024-dim, multilingual) |
| Inference | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud API (prod) |
| Agent framework | LangGraph (Supervisor–Worker) |
| Async jobs | Celery 5 + Redis 7 broker |
| Automation | Playwright + `playwright-stealth` |
| ML runtime | PyTorch (MPS on Mac, CUDA on Linux GPU) |
| Containers | Docker Compose (profiles: default, harvester) |
| License | MIT |

---

## 🗺️ Roadmap

| Phase | Theme | Status |
|---|---|---|
| **0. Harvester** | Autonomous public-data acquisition (Playwright + Stealth, cron) → Qdrant, decoupled from inference | 🟡 New |
| **2. Memory** | RAG on Qdrant + `bge-m3`, multilingual ingest pipeline, `tenant_id` enforcement | 🚧 In progress |
| **3. Brain** | LLM router + LangGraph Supervisor–Worker, Ollama/vLLM dual-engine, tool registry | ⏳ Next |
| **4. Distribution** | Playwright publisher, AES-256 session vault, peak-time scheduler | ⏳ Planned |

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

📖 **[docs/HARVESTER_GUIDE.md](./docs/HARVESTER_GUIDE.md)** — Phase 1 deep-dive: plugin architecture, CLI reference, how to add a new scraper in 30 minutes.

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

- 🛡️ **`tenant_id` everywhere.** Every Vector DB op, cache key, and audit log MUST carry `tenant_id`.
- 🧠 **Single embedding model.** `BAAI/bge-m3` is the only embedding allowed — no per-language model, no OpenAI ada.
- 🔌 **`LLMClientBase` abstraction.** Agents call `client.complete(...)` — never `openai.ChatCompletion.*` or `transformers` directly.
- ✅ **TDD mandatory.** Red → Green → Refactor. RAG/Agent logic needs **cross-language tests** (VN, EN, DE, CN).
- 🔒 **Encrypted session vault.** Playwright cookies → AES-256 → storage. Never plain-text.
- 🌾 **Zero-hardcode harvesting.** Scraping targets live in `scraper_config.yaml`, public pages only, robots.txt respected.

---

<div align="center">

**License:** [MIT](LICENSE) · Free to use, modify, and self-host. Built for the open-source AI community. 🌍

📞 **nnkienn@gmail.com**

</div>
