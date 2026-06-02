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

### 1. 🔀 Dual-Engine LLM Router (Local + Cloud)
A single `LLMClientBase` (OpenAI-compatible) interface lets every agent run on either engine **without a code change**:
- **Local / Dev tier:** Ollama or Apple MLX serving `Llama-3.1-8B-Instruct` / `Qwen2.5` → zero-cost R&D, fully offline.
- **Production / Scale tier:** vLLM on rented GPU (RunPod, AWS) or a fallback to OpenAI / Claude for peak demand.

Routing is a **runtime config decision**, never a rewrite. The same agent code runs in both tiers.

### 2. 🧠 Multi-Tenant & Multilingual RAG
- **Vector store:** [Qdrant](https://qdrant.tech/) with tenant-scoped collections.
- **Embeddings:** `BAAI/bge-m3` (1024-dim, 100+ languages) → one shared cross-lingual index, **no per-language collection**.
- **Isolation:** every `upsert` / `search` enforces a mandatory `tenant_id` payload filter. **Zero cross-tenant leakage** is an architectural guarantee, not a runtime check.
- **Cross-language retrieval:** a Vietnamese tenant can query their German-language knowledge base in one space.

### 3. 🕹️ Supervisor–Worker Agent Topology
We do **not** stuff everything into one giant prompt. Each request is decomposed into specialized roles:

| Role | Responsibility | Tools |
|---|---|---|
| **Supervisor (Planner)** | Decompose intent → ordered task graph; route to workers | Task router |
| **Researcher** | Trend-mine + tenant-scoped RAG query | `search_vector_db(tenant_id, …)` |
| **Creator** | Draft script / copy / storyboard | `generate_text`, `generate_image`, `generate_audio` |
| **Critic** | Brand-voice review + claim-vs-context anti-hallucination | RAG verifier (≤ 3 retry loops) |
| **Publisher** | Trigger Playwright auto-upload | `publish_to_platform(tenant_id, …)` |

The Critic verifies grounding before anything ships.

### 4. 📡 Omnichannel Auto-Distribution
**Redis + Celery** drain async jobs to **Playwright** headless browsers that publish while mimicking human behavior to stay within platform limits:
- YouTube Shorts · Facebook · Instagram Reels.
- Session cookies stored **AES-256 encrypted** (never plain-text).
- `playwright-stealth` to evade bot-detection.
- Schedule by tenant timezone + peak-hour heuristic.

### 5. 🌾 Autonomous Harvester
A scheduled (cron) **Playwright + Stealth** crawler that acquires **public** data, cleans it, and lands it into Qdrant tagged by `tenant_id` — fully decoupled from the agents (*Data Ingestion ≠ Inference*). Sources are declared in [`scraper_config.yaml`](./scraper_config.yaml), **never hardcoded**.

---

## 🏗️ Hexagonal Architecture

The domain core depends on nothing; the outside world plugs in through ports. You can replace Qdrant, the LLM engine, or the web framework without touching business logic.

```
n-assistant-core/
├── app/
│   ├── domain/          # Pure business entities & ports — zero framework deps
│   ├── application/     # Use cases: Supervisor-Worker agent orchestration
│   ├── infrastructure/  # Driven adapters: Qdrant · Redis/Celery · LLM clients · Playwright Harvester
│   └── api/             # Driving adapter: FastAPI routers, schemas, DI wiring
├── scraper_config.yaml  # Harvester sources — zero-hardcode (Chặng 0)
├── docker-compose.yml   # Local stack: redis + qdrant + core-api (+ harvester profile)
├── Dockerfile           # python:3.11-slim → uvicorn :8000
├── requirements.txt
└── LICENSE              # MIT
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

**Enable the Harvester** (separate process, cron-driven):

```bash
docker compose --profile harvester up -d
```

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
