<div align="center">

# N-Assistant Core 🤖🚀

### Die autonome Omnichannel-KI-Marketing-Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)

**Die MIT-lizenzierte KI-Inferenz-Engine hinter N Assistant — läuft vollständig lokal, kein Vendor-Lock-in.**

🌐 🇬🇧 [English](./README.md) · 🇻🇳 [Tiếng Việt](./README.vi.md) · 🇩🇪 **Deutsch** · 🇨🇳 [中文](./README.zh.md)

</div>

---

## 🎯 Projektvision

**N-Assistant Core** ist eine Multi-Agenten-KI-Inferenz-Engine, die **zu 100 % lokal** läuft.

Sie verbindet ein **mandantenfähiges, mehrsprachiges RAG-Gehirn (Retrieval-Augmented Generation)** mit einem von **Playwright** gesteuerten Automatisierungsarm, sodass autonome Agenten Inhalte **recherchieren → erstellen → prüfen → veröffentlichen** können — über YouTube, Facebook & Instagram, ganz ohne menschliches Eingreifen und ohne ein einziges Byte an eine Drittanbieter-Cloud zu senden, sofern *du* es nicht möchtest.

Sie richtet sich an KI- und DevOps-Ingenieure, die volle Kontrolle wollen: das LLM austauschen, den Vektorindex besitzen, den gesamten Stack selbst hosten und jede Zeile des laufenden Codes lesen.

---

## 🔥 Kern-Fähigkeiten

### 1. 🔀 Dual-Engine-LLM-Router (Lokal + Cloud)
Eine einzige `LLMClientBase`-Schnittstelle (OpenAI-kompatibel) lässt jeden Agenten auf beiden Engines laufen — **ohne Code-Änderung**:
- **Lokal- / Dev-Stufe:** Ollama oder Apple MLX mit `Llama-3.1-8B-Instruct` / `Qwen2.5` → kostenlose R&D, vollständig offline.
- **Produktions- / Scale-Stufe:** vLLM auf gemieteter GPU (RunPod, AWS) oder Fallback auf OpenAI / Claude bei Spitzenlast.

Das Routing ist eine **Laufzeit-Konfigurationsentscheidung**, nie ein Rewrite. Derselbe Agent-Code läuft auf beiden Stufen.

### 2. 🧠 Mandantenfähiges & mehrsprachiges RAG
- **Vektorspeicher:** [Qdrant](https://qdrant.tech/) mit mandantenbezogenen Collections.
- **Embeddings:** `BAAI/bge-m3` (1024-dim, 100+ Sprachen) → ein gemeinsamer sprachübergreifender Index, **keine Collection pro Sprache**.
- **Isolation:** jedes `upsert` / `search` erzwingt einen verpflichtenden `tenant_id`-Payload-Filter. **Null mandantenübergreifender Datenabfluss** ist eine Architektur-Garantie, keine Laufzeitprüfung.
- **Sprachübergreifende Abfrage:** ein vietnamesischer Mandant kann seine deutschsprachige Wissensbasis im selben Raum abfragen.

### 3. 🕹️ Supervisor–Worker-Agententopologie
Wir packen **nicht** alles in einen einzigen riesigen Prompt. Jede Anfrage wird in spezialisierte Rollen zerlegt:

| Rolle | Verantwortung | Tools |
|---|---|---|
| **Supervisor (Planner)** | Absicht zerlegen → geordneter Task-Graph; an Worker routen | Task-Router |
| **Researcher** | Trend-Mining + mandantenbezogene RAG-Abfrage | `search_vector_db(tenant_id, …)` |
| **Creator** | Skript / Copy / Storyboard entwerfen | `generate_text`, `generate_image`, `generate_audio` |
| **Critic** | Brand-Voice-Prüfung + Anti-Halluzination (Claim-vs-Context) | RAG-Verifier (≤ 3 Retry-Schleifen) |
| **Publisher** | Playwright-Auto-Upload auslösen | `publish_to_platform(tenant_id, …)` |

Der Critic prüft die Faktenbasis, bevor etwas veröffentlicht wird.

### 4. 📡 Omnichannel-Auto-Distribution
**Redis + Celery** leeren asynchrone Jobs an **Playwright**-Headless-Browser, die veröffentlichen und dabei menschliches Verhalten nachahmen, um Plattformlimits einzuhalten:
- YouTube Shorts · Facebook · Instagram Reels.
- Session-Cookies werden **AES-256-verschlüsselt** gespeichert (niemals im Klartext).
- `playwright-stealth` zur Umgehung der Bot-Erkennung.
- Planung nach Mandanten-Zeitzone + Peak-Hour-Heuristik.

### 5. 🌾 Autonomer Harvester
Ein geplanter (Cron) **Playwright + Stealth**-Crawler, der **öffentliche** Daten beschafft, bereinigt und mit `tenant_id` in Qdrant ablegt — vollständig von den Agenten entkoppelt (*Datenaufnahme ≠ Inferenz*). Quellen werden in [`scraper_config.yaml`](./scraper_config.yaml) deklariert, **niemals hartcodiert**.

---

## 🏗️ Hexagonale Architektur

Der Domänenkern hängt von nichts ab; die Außenwelt dockt über Ports an. Du kannst Qdrant, die LLM-Engine oder das Web-Framework ersetzen, ohne die Geschäftslogik anzufassen.

```
n-assistant-core/
├── app/
│   ├── domain/          # Reine Geschäftsentitäten & Ports — keine Framework-Abhängigkeiten
│   ├── application/     # Anwendungsfälle: Supervisor-Worker-Agenten-Orchestrierung
│   ├── infrastructure/  # Getriebene Adapter: Qdrant · Redis/Celery · LLM-Clients · Playwright Harvester
│   └── api/             # Treibender Adapter: FastAPI-Router, Schemas, DI-Verdrahtung
├── scraper_config.yaml  # Harvester-Quellen — zero-hardcode (Chặng 0)
├── docker-compose.yml   # Lokaler Stack: redis + qdrant + core-api (+ harvester-Profil)
├── Dockerfile           # python:3.11-slim → uvicorn :8000
├── requirements.txt
└── LICENSE              # MIT
```

---

## ⚡ Tech-Stack

| Schicht | Technologie |
|---|---|
| API | FastAPI (Python 3.11) · Pydantic v2 · SQLAlchemy 2.x |
| Vektor / RAG | **Qdrant** · `BAAI/bge-m3`-Embeddings (1024-dim, mehrsprachig) |
| Inferenz | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud API (prod) |
| Agent-Framework | LangGraph (Supervisor–Worker) |
| Async-Jobs | Celery 5 + Redis-7-Broker |
| Automatisierung | Playwright + `playwright-stealth` |
| ML-Runtime | PyTorch (MPS auf Mac, CUDA auf Linux-GPU) |
| Container | Docker Compose (Profile: default, harvester) |
| Lizenz | MIT |

---

## 🗺️ Roadmap

| Phase | Thema | Status |
|---|---|---|
| **0. Harvester** | Autonome Beschaffung öffentlicher Daten (Playwright + Stealth, Cron) → Qdrant, von Inferenz entkoppelt | 🟡 Neu |
| **2. Memory** | RAG auf Qdrant + `bge-m3`, mehrsprachige Ingest-Pipeline, `tenant_id`-Erzwingung | 🚧 In Arbeit |
| **3. Brain** | LLM-Router + LangGraph Supervisor–Worker, Ollama/vLLM Dual-Engine, Tool-Registry | ⏳ Als Nächstes |
| **4. Distribution** | Playwright-Publisher, AES-256-Session-Vault, Peak-Time-Scheduler | ⏳ Geplant |

---

## 🚀 Schnellstart

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # startet redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

Fertig — eine vollständige lokale KI-Engine unter `http://localhost:8000`.

| Dienst | URL |
|---|---|
| Core API (RAG / LLM) | http://localhost:8000 |
| Qdrant (Vektor-DB) | http://localhost:6333 |
| Redis (Broker) | localhost:6379 |

**Harvester aktivieren** (separater Prozess, cron-gesteuert):

```bash
docker compose --profile harvester up -d
```

---

## 🔐 Nicht verhandelbare Engineering-Regeln

Diese sind **konstitutionell**. PRs, die sie verletzen, werden automatisch abgelehnt.

- 🛡️ **`tenant_id` überall.** Jede Vektor-DB-Operation, jeder Cache-Key und jedes Audit-Log MUSS `tenant_id` tragen.
- 🧠 **Einziges Embedding-Modell.** `BAAI/bge-m3` ist das einzige erlaubte Embedding — kein Modell pro Sprache, kein OpenAI ada.
- 🔌 **`LLMClientBase`-Abstraktion.** Agenten rufen `client.complete(...)` auf — niemals direkt `openai.ChatCompletion.*` oder `transformers`.
- ✅ **TDD verpflichtend.** Red → Green → Refactor. RAG-/Agent-Logik braucht **sprachübergreifende Tests** (VN, EN, DE, CN).
- 🔒 **Verschlüsselter Session-Vault.** Playwright-Cookies → AES-256 → Speicher. Niemals im Klartext.
- 🌾 **Zero-Hardcode-Harvesting.** Scraping-Ziele stehen in `scraper_config.yaml`, nur öffentliche Seiten, robots.txt wird respektiert.

---

<div align="center">

**Lizenz:** [MIT](LICENSE) · Frei nutzbar, modifizierbar und selbst hostbar. Gebaut für die Open-Source-KI-Community. 🌍

📞 **nnkienn@gmail.com**

</div>
