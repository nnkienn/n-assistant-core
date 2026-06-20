<div align="center">

# Nyxara 🤖🚀

### KI-Engineering richtig lernen — eine mehrsprachige RAG- + Agenten-Engine von Grund auf bauen, ausgerichtet auf eine konkrete Nische

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)

**Die meisten „KI lernen"-Nebenprojekte sterben als zusammengeklebte Tutorials ohne Nutzer und ohne jede Möglichkeit zu erkennen, ob irgendetwas funktioniert. Nyxara setzt auf das Gegenteil: Du baust jede Schicht selbst — Advanced RAG, Fine-tuning, Agenten-Workflows, Evaluation — und richtest sie auf eine echte Aufgabe aus: einen *Comment Assistant* für TikTok-Shop- / Shopee-Seller-Affiliates. Mensch in der Schleife, nie Auto-Posting.**

🌐 🇬🇧 [English](./README.md) · 🇻🇳 [Tiếng Việt](./README.vi.md) · 🇩🇪 **Deutsch** · 🇨🇳 [中文](./README.zh.md)

</div>

---

## 🎯 Warum es das gibt

Zwei Dinge töten die meisten „Ich lerne KI-Engineering"-Projekte:

1. **Sie sind aus Tutorials zusammengenäht.** Du verdrahtest einen LangChain-Retriever, bekommst eine Antwort und lernst nie, *warum* dense Retrieval danebenlag, was RRF eigentlich berechnet oder ob dein Reranker geholfen hat. Das Verständnis bleibt nie hängen.
2. **Sie haben kein Ziel.** Keine echte Aufgabe, kein echter Nutzer, keine Möglichkeit „besser" zu messen. Die Motivation verfliegt.

**Nyxara behebt beides.** Es ist eine mehrsprachige **RAG- + Agenten-Engine, die du von Grund auf baust** — du besitzt die Embedding-Mathematik, die RRF-Formel, das Cross-Encoder-Rerank, das LoRA-Update, die Eval-Metriken — und sie ist auf eine **konkrete Nische mit echten (wenn auch kleinen) Nutzern** ausgerichtet: Content- & Social-Automatisierung für **Seller-Affiliates auf TikTok Shop / Shopee in Vietnam.**

> **Für die Leserin / den Leser:** Wenn du KI-Engineering *verstehen* willst — nicht nur eine API aufrufen — indem du ein kohärentes System mit einem echten, demonstrierbaren und messbaren Ziel baust, dann ist dieses Repo für dich. Es ist **zuerst ein Lernvehikel**, dann ein Nischenwerkzeug. Kein Multi-Tenant-SaaS, kein Marktspiel.

Es läuft standardmäßig **100% lokal** (kein Byte verlässt deine Maschine, es sei denn, du wählst eine Cloud-Stufe), und eine `tenant_id` als **Namespace** lässt eine Installation mehrere Nischen nebeneinander beherbergen — *Ordner pro Nische*, nicht *Tenant pro zahlendem Kunden*. Kein Billing, keine Auth, kein Dashboard.

---

## 🛍️ Leitanwendung — der Comment Assistant

Das ist das Nischenziel, das jeder Technik einen Daseinsgrund gibt.

Ein Seller-Affiliate postet ein Produktvideo auf TikTok Shop / Shopee. Darunter häufen sich Dutzende Kommentare: *„Wie viel kostet das?"*, *„Geht das bei fettiger Haut?"*, *„Wie lange dauert der Versand?"*. Der Comment Assistant verwandelt diesen Schwall in geprüfte, markenkonforme Antworten:

1. **Lesen** der öffentlichen Kommentare unter dem Video.
2. **Abrufen** der richtigen Produktfakten — Preis, Inhaltsstoffe, Anwendung, offizieller Link — **gefiltert auf *genau dieses Produkt*** (erst Metadaten-Filter, *dann* semantische Suche — nicht „der nächste Vektor gewinnt").
3. **Entwerfen** einer Antwort in der Stimme und Sprache des Sellers.
4. **Kritik:** ein dedizierter **Critic-Agent blockiert erfundene Fakten und unbelegte Wirkungsversprechen** — unverhandelbar bei Kosmetik/Gesundheit, wo ein falsches Versprechen ein Vertrauens- und Rechtsproblem ist.
5. **Ein Mensch genehmigt**, bevor irgendetwas gesendet wird. **Nyxara postet nie automatisch.** Wenn eine Antwort *gesendet* wird, läuft sie über die **offizielle API** der Plattform — nie über einen Stealth-Browser.

Jede RAG-/Agenten-/Eval-Technik unten verdient sich ihren Platz, indem sie hier eine echte Frage beantwortet: *Hat das Retrieval das richtige Produkt gezogen? Hat das Rerank die Antwort wirklich verbessert? Hat der Critic das falsche Versprechen erwischt?*

---

## 🔥 Kernfähigkeiten

### 1. 🌾 Pluggable Harvester — Jede Plattform, Community-getrieben
**Das ist Phase 0 — das Fundament, von dem alles andere lebt.** Ein geplanter (Cron) Crawler erfasst **öffentliche** Daten — **Produktinformationen und öffentliche Kommentar-Beispiele** für den Comment Assistant — stempelt sie mit einem `tenant_id`-Namespace, legt sie in einem nischenweisen **Raw Data Lake** ab und reinigt sie dann durch einen 3-Schichten-Anti-Spam-Filter — vollständig von den Agenten entkoppelt (*Datenerfassung ≠ Inferenz*; diese Schicht ruft **nie** ein LLM auf).

**Binde jede Plattform ein — lege eine Datei ab.** Die Engine erkennt zur Laufzeit automatisch jedes Plugin unter [`extractors/plugins/`](./app/infrastructure/harvester/extractors/plugins/). Eine neue Quelle ist eine Klasse — keine Core-Änderungen, keine hartkodierten Imports:

```python
class MyPlatformExtractor(BaseExtractor):
    PLUGIN_TYPE = "my_platform"          # ← referenziert über `type:` in scraper_config.yaml
    async def extract(self) -> list[HarvestedItem]:
        url = self.options["url"]        # alles aus YAML — zero-hardcode
        ...
```

Ein abstürzendes Plugin wird geloggt und übersprungen — eine schlechte Quelle reißt nie den ganzen Lauf nieder.

**Heute ausgeliefert:** `x_twscrape` (X / Twitter via twscrape) · `youtube_shorts` (YouTube Shorts via yt-dlp).
**Wir brauchen deine Hilfe** 🤝 — öffentliche Seiten ändern ständig Markup und Rate-Limits. Trage ein neues Plattform-Plugin bei (TikTok, Shopee, Instagram, Reddit…) oder hilf, einen bestehenden Extraktor **robust und ToS-konform** zu halten. Der ganze Vertrag ist eine Datei: [`base.py`](./app/infrastructure/harvester/extractors/base.py).

**3-Schichten-Anti-Spam-Filter** — fail-fast und kostenbewusst; jedes Item muss sich die nächste Schicht verdienen, sodass der bezahlte LLM-Aufruf nur sieht, was bereits zwei kostenlose CPU-Gates überlebt hat:

| Schicht | Stufe | Kosten | Verwirft |
|---|---|---|---|
| **L1** | Heuristik (Hashtag- / Wortzahl- / Mention-Gates) | O(1) CPU | Engagement-Bait, Einzeiler, Mass-Mention-Spam |
| **L2** | Text-Clean (URLs, Emojis, Boilerplate entfernen) | O(n) CPU | nach Reinigung leere Items |
| **L3** | LLM-Judge (gebündelt, OpenAI-kompatibel) | ~1 API-Call / 10 Items | Witze, Replies, Geschwätz mit geringem Wert |

Freigegebene Items landen in `raw_data_lake/filtered/approved.json`, Qdrant-bereit. Quellen und Schwellen leben in [`scraper_config.yaml`](./scraper_config.yaml) → `filter_config`, **nie hartkodiert**.

### 2. 🔀 Dual-Engine-LLM-Router (Lokal + Cloud)
Eine einzige `LLMClientBase` (OpenAI-kompatible) Schnittstelle lässt jeden Agenten auf beiden Engines laufen — **ohne Code-Änderung**:
- **Lokal- / Dev-Stufe:** Ollama oder Apple MLX mit `Qwen2.5` / `Llama-3.1-8B-Instruct` → kostenfreies R&D, vollständig offline.
- **Scale-Stufe:** vLLM auf gemieteter GPU (RunPod, AWS) oder Fallback auf eine Cloud-API für schwere Batches.

Das Routing ist eine **Laufzeit-Konfigurationsentscheidung**, nie ein Rewrite. Derselbe Agenten-Code läuft in beiden Stufen.

> **Hardware-Erwartungen (ehrlich):** die CORE-Phasen laufen bequem auf einer CPU-/No-GPU-Box mit einem lokalen 3B-Modell. Aber das **Critic-/CRAG-Grading** will ein leistungsfähiges Modell — auf einer reinen 3B-Box ist dieses Urteilen *best-effort*, also route Tier-1 auf eine Cloud-/Hybrid-Engine, wenn du starke Anti-Halluzination brauchst. Die **OPTIONALE Visual Engine (ComfyUI Bild/Video + TTS) braucht eine echte GPU** und ist nicht realistisch CPU-lokal. „100% lokal" gilt durchgängig auf einer GPU-Box; auf reiner CPU-Hardware deckt es das RAG-/Agenten-Gehirn ab, nicht den optionalen Visual-Track.

### 3. 🧠 Multi-Nische & mehrsprachiges RAG
- **Vektorspeicher:** [Qdrant](https://qdrant.tech/) mit namespace-gebundenen Collections.
- **Embeddings:** `BAAI/bge-m3` (1024-dim, 100+ Sprachen) → ein gemeinsamer sprachübergreifender Index, **keine Collection pro Sprache**.
- **Namespace-Isolation:** jedes `upsert` / `search` trägt einen verpflichtenden `tenant_id`-Payload-Filter, sodass mehrere Nischen in einem Speicher koexistieren — mit **null nischenübergreifendem Durchsickern**, eine Architekturgarantie, keine Laufzeitprüfung.
- **Sprachübergreifendes Retrieval:** eine vietnamesische Nische kann ihre deutschsprachige Wissensbasis in einem Raum abfragen.
- **Was du hier lernst:** Chunking-Strategie, die Embedding-Mathematik, Cosinus-Ähnlichkeit von Hand, dann den vollen **Advanced-RAG-Stack aus Phase 3** — Hybrid Search, RRF, Cross-Encoder-Reranking, CRAG, Query-Transformation und gemessene Evaluation (siehe Roadmap unten).

### 4. 🕹️ Supervisor–Worker-Agenten-Topologie
Wir stopfen **nicht** alles in einen riesigen Prompt. Jede Anfrage wird in spezialisierte Rollen zerlegt:

| Rolle | Verantwortung | Werkzeuge |
|---|---|---|
| **Supervisor (Planner)** | Intent zerlegen → geordneter Task-Graph; an Worker routen | Task-Router |
| **Researcher** | Namespace-gebundene RAG-Abfrage (treibt die Phase-3-Pipeline) | `search_vector_db(tenant_id, …)` |
| **Creator** | Antwort / Copy in der Stimme des Sellers entwerfen | `generate_text` |
| **Critic** | Anti-Halluzination: erfundene Fakten & unbelegte Wirkungsversprechen blockieren | RAG-Verifier (≤ 3 Retry-Schleifen) |
| **Human Reviewer** | Genehmigen / bearbeiten / ablehnen, bevor etwas gesendet wird — **die Schleife schließt sich auf einem Menschen, nicht auf Auto-Send** | Review-Queue |

Der **Critic ist der Burggraben**: Er prüft die Verankerung, bevor ein Entwurf den Menschen erreicht, und der Mensch ist das letzte Tor. **Es gibt keinen Auto-Publish-Agenten.** Wenn eine genehmigte Antwort gesendet wird, läuft sie über die **offizielle API** der Plattform.

> Der Agenten-Graph ist plugin-förmig: Der OPTIONALE Visual-Track (spätere Phase) kann einen **Visual Director** und einen **Video Producer** als Knoten hinzufügen, ohne die Verträge der bestehenden Rollen zu ändern.

---

## 🏗️ Hexagonale Architektur

Der Domain-Kern hängt von nichts ab; die Außenwelt steckt sich über Ports ein. Du kannst Qdrant, die LLM-Engine oder das Web-Framework ersetzen, ohne die Geschäftslogik anzufassen.

```
n-assistant-core/
├── app/
│   ├── domain/                  # Reine Geschäftsentitäten & Ports — null Framework-Deps
│   ├── application/             # Use Cases + Filter-Pipelines (3-Schichten-Anti-Spam)
│   ├── infrastructure/
│   │   └── harvester/           # engine.py · extractors/plugins/ (X, YouTube…) · filters/
│   └── api/                     # Driving Adapter: FastAPI-Router, Schemas, DI-Verdrahtung
├── cli.py                       # ★ Einheitliche CLI — einziger Einstiegspunkt für alle Harvest-Ops
├── scraper_config.yaml          # Harvester-Quellen + Filter-Schwellen — zero-hardcode
├── raw_data_lake/               # Landezone pro Namespace: texts/ (roh) + filtered/ (sauber)
├── docker-compose.yml           # redis + qdrant + core-api (+ Harvester-Profil)
├── Dockerfile · Dockerfile.harvester   # core-API-Image · Chromium-Image für Plugins
├── requirements.txt
└── LICENSE                      # MIT
```

---

## ⚡ Tech-Stack

| Schicht | Technologie |
|---|---|
| API | FastAPI (Python 3.11) · Pydantic v2 · SQLAlchemy 2.x |
| Vector / RAG | **Qdrant** · `BAAI/bge-m3`-Embeddings (1024-dim, mehrsprachig) · Hybrid + RRF + **Cross-Encoder-Rerank (`bge-reranker-v2-m3`)** + CRAG · Metadaten-Filter · Semantic Chunking |
| Inferenz | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud-API (scale) |
| Fine-tuning | LoRA auf `Qwen2.5-7B` · GGUF-Quantisierungs-Merge (Q4/Q5/Q8) · Embedding-/Domain-Fine-tuning |
| Agenten-Framework | LangGraph (Supervisor–Worker, Multi-Agent, Human-in-the-Loop) |
| Eval | **RAGAS** (Faithfulness, Answer Relevancy, Context Precision/Recall) + Custom-Metriken + A/B-Umschaltung — **ab Phase 3** |
| Async-Jobs | Celery 5 + Redis-7-Broker |
| MLOps (Phase 6) | LangFuse / Prometheus + Grafana · DVC / W&B / MLflow (leicht) · CI/CD-Retrain |
| Visual / Video — *OPTIONAL* | ComfyUI · Flux / SDXL · ControlNet · IP-Adapter / FaceID · XTTS / CosyVoice · ffmpeg *(braucht GPU)* |
| ML-Runtime | PyTorch (MPS auf Mac, CUDA auf Linux-GPU) |
| Container | Docker Compose (Profile: default, harvester, rag) |
| Lizenz | MIT |

---

## 🗺️ Roadmap — Ein Lernpfad

Die Phasen sind so geordnet, dass jede eine Schicht des Stacks von Grund auf lehrt. Der Status ist ehrlich, nicht aspirational. **CORE**-Phasen sind der Haupt-Lernpfad; der **OPTIONALE** Visual-Track liegt daneben — die Architektur lässt dich ihn später anschrauben, *ohne* das Gebaute zu zerbrechen, aber er lehrt Diffusion/Video, nicht die zentrale KI-Engineering-Route.

| Phase | Track | Thema | Was du baust & lernst | Status |
|---|---|---|---|---|
| **0. Fundament** | CORE | Harvester: **Produktdaten + öffentliche Kommentar-Beispiele** · sauberes MIT-Repo · Beispiele pro Nische | Plugin-Architektur, Zero-Hardcode-Config, 3-Schichten-Filter | 🟢 Fertig |
| **1. Skelett** | CORE | FastAPI-Core, `/health`, Docker, einheitliche CLI | Hexagonale Architektur, Container-Workflow | ✅ Fertig |
| **2. Vektor-Gedächtnis** | CORE | Chunking + `bge-m3` + Qdrant + Multi-Namespace | Embedding-Mathematik, Cosinus-Ähnlichkeit **von Hand**, Namespace-Isolation | ✅ Fertig |
| **3. Advanced RAG + Eval** | CORE | Das volle Retrieval-Gehirn — **siehe Deep-Dive-Tabelle unten** — plus gemessene Evaluation (RAGAS + A/B) fest eingebaut | RRF- & Rerank-Mathematik, Query↔Doc-Raum, Chunk-Granularität, Token-Budget, Graph-Workflows, *messen, ob jede Technik hilft* | ⏳ In Arbeit |
| **4. Fine-tuning** | CORE | **LoRA** auf `Qwen2.5-7B` · GGUF-Merge · Multi-Domain-Dataset · **Embedding-/Domain-Fine-tuning** | Low-Rank-Update-Mathematik, Quantisierung, Dataset- & Embedding-Tuning-Design | ⏳ Geplant |
| **5. Agentic Orchestrator** | CORE | LangGraph-Supervisor–Worker (Researcher → Creator → **Critic**) · **Comment Assistant** end-to-end · **Human-in-the-Loop-Review** · Domain-Router | Multi-Agent-Design, Grounding & Anti-Halluzination, HITL-Workflows, Nischen-Routing | ⏳ Geplant |
| **6. Production, MLOps & Eval** | CORE | Voller Docker-Stack · Monitoring/Logging (LangFuse, Prometheus + Grafana) · `config.yaml` · CI/CD-Retrain · Experiment-Tracking (W&B / MLflow) · Versionierung (DVC / HF Hub) | Observability, reproduzierbares ML, schweres MLOps | ⏳ Geplant |
| **7. Community & Erweiterbarkeit** | CORE | Nischen-Templates (Seller-Affiliate, Beauty, Tech…) · Plugin-Architektur (Scraper / LLM-Client) · Beispielprojekte | OSS-Erweiterbarkeit, Plugin-Design | ⏳ Geplant |
| **★ Visual & Character Engine** | **OPTIONAL** | ComfyUI + IP-Adapter / FaceID + Character-LoRA · Flux/SDXL + ControlNet · Image/Text→Video · Lip-Sync + TTS-Clone (XTTS/CosyVoice) · ffmpeg-Auto-Edit | Konsistenztechniken, Diffusionssteuerung, Video-Pipeline | 🧩 Add-on · braucht GPU |

### Phase 3 im Detail — Advanced RAG, jede Technik pro Query zuschaltbar

Der ganze Sinn von Phase 3 ist, jede Technik **von Hand** zu bauen (reines Python über `LLMClientBase` + `qdrant-client`, LangGraph nur für den Fluss) und dann **zu messen, ob sie wirklich hilft** — *RAG ohne Messen zu lernen, heißt blind zu lernen.*

| Technik | Was sie tut | Was du lernst |
|---|---|---|
| **Hybrid Search** (dense + sparse/BM25) | semantisches + Keyword-Retrieval zusammen ausführen | wann dense sparse schlägt und wann sparse dense schlägt |
| **RRF** (Reciprocal Rank Fusion) | mehrere Ranglisten zu einer verschmelzen | die RRF-Formel von Hand; wie man Rankings fusioniert |
| **Cross-Encoder-Reranking** (`bge-reranker-v2-m3`, gleiche Familie wie bge-m3) | Top-k neu bewerten, indem Query+Doc *zusammen* gelesen werden | warum Reranking die Top-k-Qualität nach dem Retrieval am stärksten hebt; **Bi-Encoder vs Cross-Encoder** |
| **CRAG** (Corrective RAG) via LangGraph | abgerufenen Kontext bewerten, dann Retry / Verbreitern / Eskalation | Selbstbewertung des Kontexts; selbstkorrigierende Retrieval-Schleifen |
| **Query Transformation** (Multi-Query + HyDE) | die Query vor der Suche erweitern / umschreiben | die Query↔Dokument-Raum-Diskrepanz und wie man sie schließt |
| **Parent-Child** (Small-to-Big) Retrieval | auf kleinen Chunks matchen, den großen Parent-Block zurückgeben | präziser Match *und* voller Kontext; Chunk-Granularität |
| **Context Compression** | abgerufene Chunks auf nur die antwortenden Sätze trimmen | Rauschen schneiden; Token-Budget-Management auf einem kleinen lokalen LLM |
| **Metadaten-Filterung** (Vektor + Filter) | auf das richtige Produkt / die richtige Preisspanne *vor* der semantischen Suche filtern | strukturierten Filter + Vektorsuche kombinieren — **live im Comment Assistant genutzt** |
| **Semantic Chunking** | nach Bedeutung teilen, nicht nach fester Länge | wie Chunk-Granularität die Retrieval-Qualität formt |
| **Evaluation** (RAGAS + Custom + A/B) | Faithfulness, Answer Relevancy, Context Precision/Recall | **ob Rerank / CRAG / Rewrite wirklich verbessern** — von „viel später" nach *jetzt* gezogen |

Jede Technik ist ein **Per-Query-Flag**, standardmäßig aus, sodass du *mit* vs *ohne* A/B-testen und die Metriken lesen kannst. Schweres MLOps (LangFuse/Prometheus/Grafana, CI/CD-Retrain) bleibt in Phase 6 — nur die **Basis-Eval (RAGAS + A/B-Vergleich)** kommt nach Phase 3.

### Was du tief lernst
- **Mathematik:** Embeddings, Cosinus-Ähnlichkeit, RRF, **Cross-Encoder-Reranking**, Low-Rank-Adaptation (LoRA), Quantisierung, **RAG-Evaluationsmetriken**.
- **Architektur:** Advanced RAG, Agentic Workflows (LangGraph), Vektor-DB, Multi-Namespace, Human-in-the-Loop.
- **Production:** Fine-tuning, Quantisierung, Pipeline-Orchestrierung, Evaluation, leichtes MLOps.
- **Engineering:** modularer Code, Docker, API-Design, Open-Source-Best-Practices.
- **Optional / Visual AI:** ComfyUI-Workflows, ControlNet, Charakter-/Identitätskonsistenz *(wenn du den optionalen Track auf einer GPU-Box hinzufügst)*.

---

## 🚀 Schnellstart

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # startet redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

Das war's — eine vollständige lokale KI-Engine auf `http://localhost:8000`.

| Dienst | URL |
|---|---|
| Core API (RAG / LLM) | http://localhost:8000 |
| Qdrant (Vektor-DB) | http://localhost:6333 |
| Redis (Broker) | localhost:6379 |

📖 **[docs/HARVESTER_GUIDE.md](./docs/HARVESTER_GUIDE.md)** — Phase-0-Deep-Dive: Plugin-Architektur, CLI-Referenz, wie man in 30 Minuten einen neuen Scraper hinzufügt.

**Die Daten-Pipeline ausführen** — ernten, dann filtern, **vollständig über Docker** (kein lokales Python, kein venv). Ein dünner Wrapper führt die einheitliche `cli.py` *innerhalb* des Harvester-Containers aus:

```bash
# Linux / macOS: ./nassistant.sh <befehl>      Windows: .\nassistant.ps1 <befehl>

# Alle registrierten Plugins + ihren An/Aus-Status in config/scraper_config.yaml zeigen
./nassistant.sh list-plugins

# Ernten: jede aktivierte Quelle scrapen → Raw Data Lake
./nassistant.sh harvest

# Eine einzelne benannte Quelle ernten (erst dry-run zur Vorschau)
./nassistant.sh harvest --source product-catalog-demo --dry-run
./nassistant.sh harvest --source product-catalog-demo

# Alle Quellen eines Plugin-Typs ernten, je 5 Items begrenzt
./nassistant.sh harvest --type youtube_shorts --limit 5

# Filtern: die 3-Schichten-Anti-Spam-Pipeline über alle geernteten Daten laufen lassen
./nassistant.sh filter

# Nur einen Plugin-Typ filtern
./nassistant.sh filter --type youtube_shorts
```

Führe `./nassistant.sh --help` oder `./nassistant.sh <befehl> --help` aus, um alle Optionen zu sehen.

> **Schicht 3 ruft ein LLM auf**, also setze zuerst `INFERENCE_PROVIDER` / `INFERENCE_BASE_URL` / `INFERENCE_MODEL` / `INFERENCE_API_KEY` in `.env` — Gemini, OpenAI oder lokales Ollama (jeder OpenAI-kompatible Endpunkt). Schichten 1–2 sind reine CPU und laufen ohne Key.

<details>
<summary>Lieber rohes <code>docker compose</code>? (kein Wrapper)</summary>

Der Wrapper ist nur ein Einzeiler um `docker compose run`. Das Harvester-Image liefert `cli.py` mit, sodass jeder Unterbefehl funktioniert:

```bash
docker compose --profile harvester run --rm harvester python cli.py list-plugins
docker compose --profile harvester run --rm harvester python cli.py harvest
docker compose --profile harvester run --rm harvester python cli.py filter
```

</details>

---

## 🔐 Nicht verhandelbare Engineering-Regeln

Diese sind **konstitutionell**. PRs, die sie verletzen, werden automatisch abgelehnt.

- 🛡️ **Namespace überall.** Jede Vector-DB-Op, jeder Cache-Key und jeder Audit-Log MUSS einen `tenant_id`-Namespace tragen, damit Nischen nie ineinander durchsickern.
- 🧠 **Ein einziges Embedding-Modell.** `BAAI/bge-m3` ist das einzig erlaubte Embedding — kein Modell pro Sprache, kein OpenAI ada.
- 🔌 **`LLMClientBase`-Abstraktion.** Agenten rufen `client.complete(...)` — nie `openai.ChatCompletion.*` oder `transformers` direkt.
- ✅ **TDD verpflichtend.** Red → Green → Refactor. RAG/Agent-Logik braucht **sprachübergreifende Tests** (VN, EN, DE, CN).
- 🙋 **Human-in-the-Loop, kein Auto-Publishing.** Entwürfe gehen an einen Menschen zum Genehmigen, Bearbeiten oder Ablehnen. Nichts wird autonom gesendet; wenn Inhalt *gesendet* wird, nutzt er die **offizielle API** der Plattform — nie Browser-Automatisierung / Stealth-Posting.
- 🌾 **Zero-Hardcode-Harvesting.** Scraping-Ziele leben in `scraper_config.yaml`, nur öffentliche Seiten, robots.txt respektiert.

---

<div align="center">

**Lizenz:** [MIT](LICENSE) · Frei zu nutzen, zu forken, zu ändern und selbst zu hosten. Gebaut für die Open-Source-KI-Community. 🌍

📞 **nnkienn@gmail.com**

</div>
