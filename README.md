<div align="center">

# N-Assistant Core 🤖🚀

### The Autonomous Omnichannel AI Marketing Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)

**100% Free & Open-Source AI inference engine — runs fully local, no vendor lock-in.**

🇬🇧 [English](#-english) · 🇻🇳 [Tiếng Việt](#-tiếng-việt) · 🇩🇪 [Deutsch](#-deutsch) · 🇨🇳 [中文](#-中文)

</div>

---

## 🇬🇧 English

### 🎯 Project Vision

**N-Assistant Core** is a multi-agent AI inference engine built to run **100% locally**.
It fuses a **Retrieval-Augmented Generation (RAG)** brain with a **Playwright**-driven
automation arm, so autonomous agents can research, create, review and **publish content
across multiple channels** without any human in the loop — and without sending a single
byte to a third-party cloud unless *you* choose to.

It is engineered for AI and DevOps engineers who want full control: swap the LLM, own the
vector index, self-host the whole stack, and read every line of the code that runs it.

### 🏗️ Core Architecture

| Pillar | What it does |
|---|---|
| **🔀 Dual-Engine LLM Router** | A single `LLMClientBase` interface routes inference to **offline** engines (Ollama / Apple MLX serving Llama-3.1 / Qwen2.5) or **online** APIs (OpenAI / Claude). Switching engines is a config flag — never a code change. |
| **🧠 Multi-tenant & Multilingual RAG** | **Qdrant** vector store + **`BAAI/bge-m3`** embeddings give one shared cross-lingual space (VN/EN/DE/CN). Every `upsert`/`search` is isolated by a mandatory `tenant_id` payload filter. |
| **🕹️ Supervisor–Worker Agentic Pattern** | A Planner decomposes intent into a task graph; specialized workers (Researcher → Creator → Critic → Publisher) each run with minimal context. The Critic verifies grounding before anything ships. |
| **📡 Omnichannel Auto-Distribution** | **Redis + Celery** drain async jobs to **Playwright** headless browsers that publish to social platforms, mimicking human behavior to stay within platform limits. |

### 📂 Directory Structure (Hexagonal Architecture)

```
n-assistant-core/
├── app/
│   ├── domain/          # Pure business entities & ports — zero framework deps
│   ├── application/     # Use cases: Supervisor-Worker agent orchestration
│   ├── infrastructure/  # Driven adapters: Qdrant, Redis/Celery, LLM clients, Playwright
│   └── api/             # Driving adapter: FastAPI routers, schemas, DI wiring
├── Dockerfile           # python:3.11-slim → uvicorn :8000
├── docker-compose.yml   # local stack: redis + qdrant + core-api
├── requirements.txt
└── LICENSE              # MIT
```

The domain core depends on nothing; the outside world plugs in through ports. You can
replace Qdrant, the LLM engine, or the web framework without touching business logic.

### ⚡ Quick Start

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # spins up redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

That's it — a full local AI engine on `http://localhost:8000`.

---

<details>
<summary><h2>🇻🇳 Tiếng Việt</h2></summary>

### 🎯 Tầm nhìn dự án

**N-Assistant Core** là một động cơ suy luận AI đa đại lý (multi-agent) được thiết kế để
chạy **100% trên máy local**. Nó kết hợp bộ não **RAG (Retrieval-Augmented Generation)**
với cánh tay tự động hóa điều khiển bằng **Playwright**, cho phép các agent tự hành nghiên
cứu, sáng tạo, kiểm duyệt và **phân phối nội dung đa kênh** mà không cần con người can
thiệp — và không gửi một byte dữ liệu nào lên cloud bên thứ ba trừ khi *bạn* muốn.

Dự án dành cho các kỹ sư AI và DevOps muốn toàn quyền kiểm soát: thay LLM tùy ý, sở hữu
chỉ mục vector, tự host toàn bộ hệ thống, và đọc được từng dòng code đang chạy.

### 🏗️ Kiến trúc Công nghệ Lõi

| Trụ cột | Vai trò |
|---|---|
| **🔀 Bộ định tuyến LLM Song Động cơ** | Một giao diện `LLMClientBase` duy nhất định tuyến suy luận tới engine **offline** (Ollama / Apple MLX chạy Llama-3.1 / Qwen2.5) hoặc API **online** (OpenAI / Claude). Đổi engine chỉ là một flag cấu hình — không phải sửa code. |
| **🧠 RAG Đa người dùng & Đa ngôn ngữ** | Vector store **Qdrant** + embedding **`BAAI/bge-m3`** tạo một không gian xuyên ngôn ngữ chung (VN/EN/DE/CN). Mọi `upsert`/`search` đều bị cô lập bằng bộ lọc payload `tenant_id` bắt buộc. |
| **🕹️ Mô hình Agentic Supervisor–Worker** | Một Planner phân rã ý định thành đồ thị tác vụ; các worker chuyên biệt (Researcher → Creator → Critic → Publisher) chạy với ngữ cảnh tối thiểu. Critic kiểm chứng tính xác thực trước khi xuất bản. |
| **📡 Tự động Phân phối Đa kênh** | **Redis + Celery** rút hàng đợi tác vụ bất đồng bộ tới trình duyệt headless **Playwright** để đăng lên các nền tảng mạng xã hội, mô phỏng hành vi người dùng để tránh giới hạn nền tảng. |

### 📂 Cấu trúc thư mục (Kiến trúc Hexagonal)

```
n-assistant-core/
├── app/
│   ├── domain/          # Thực thể nghiệp vụ thuần & các port — không phụ thuộc framework
│   ├── application/     # Use case: điều phối agent Supervisor-Worker
│   ├── infrastructure/  # Adapter bị điều khiển: Qdrant, Redis/Celery, LLM client, Playwright
│   └── api/             # Adapter điều khiển: router FastAPI, schema, nối DI
├── Dockerfile           # python:3.11-slim → uvicorn :8000
├── docker-compose.yml   # stack local: redis + qdrant + core-api
├── requirements.txt
└── LICENSE              # MIT
```

Lõi domain không phụ thuộc gì cả; thế giới bên ngoài cắm vào qua các port. Bạn có thể thay
Qdrant, engine LLM hay web framework mà không cần động đến logic nghiệp vụ.

### ⚡ Bắt đầu nhanh

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # khởi chạy redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

Vậy là xong — một động cơ AI local hoàn chỉnh tại `http://localhost:8000`.

</details>

---

<details>
<summary><h2>🇩🇪 Deutsch</h2></summary>

### 🎯 Projektvision

**N-Assistant Core** ist eine Multi-Agenten-KI-Inferenz-Engine, die **zu 100 % lokal**
läuft. Sie verbindet ein **RAG-Gehirn (Retrieval-Augmented Generation)** mit einem von
**Playwright** gesteuerten Automatisierungsarm, sodass autonome Agenten recherchieren,
erstellen, prüfen und **Inhalte über mehrere Kanäle veröffentlichen** können — ganz ohne
menschliches Eingreifen und ohne ein einziges Byte an eine Drittanbieter-Cloud zu senden,
sofern *du* es nicht möchtest.

Sie richtet sich an KI- und DevOps-Ingenieure, die volle Kontrolle wollen: das LLM
austauschen, den Vektorindex besitzen, den gesamten Stack selbst hosten und jede Zeile
des laufenden Codes lesen.

### 🏗️ Kern-Architektur

| Säule | Funktion |
|---|---|
| **🔀 Dual-Engine-LLM-Router** | Eine einzige `LLMClientBase`-Schnittstelle leitet die Inferenz an **Offline**-Engines (Ollama / Apple MLX mit Llama-3.1 / Qwen2.5) oder **Online**-APIs (OpenAI / Claude) weiter. Ein Engine-Wechsel ist ein Config-Flag — keine Code-Änderung. |
| **🧠 Mandantenfähiges & mehrsprachiges RAG** | **Qdrant**-Vektorspeicher + **`BAAI/bge-m3`**-Embeddings ergeben einen gemeinsamen sprachübergreifenden Raum (VN/EN/DE/CN). Jedes `upsert`/`search` wird durch einen verpflichtenden `tenant_id`-Payload-Filter isoliert. |
| **🕹️ Supervisor–Worker-Agentenmuster** | Ein Planner zerlegt die Absicht in einen Task-Graphen; spezialisierte Worker (Researcher → Creator → Critic → Publisher) laufen mit minimalem Kontext. Der Critic prüft die Faktenbasis, bevor etwas veröffentlicht wird. |
| **📡 Omnichannel-Auto-Distribution** | **Redis + Celery** leeren asynchrone Jobs an **Playwright**-Headless-Browser, die auf Social-Plattformen veröffentlichen und menschliches Verhalten nachahmen, um Plattformlimits einzuhalten. |

### 📂 Verzeichnisstruktur (Hexagonale Architektur)

```
n-assistant-core/
├── app/
│   ├── domain/          # Reine Geschäftsentitäten & Ports — keine Framework-Abhängigkeiten
│   ├── application/     # Anwendungsfälle: Supervisor-Worker-Agenten-Orchestrierung
│   ├── infrastructure/  # Getriebene Adapter: Qdrant, Redis/Celery, LLM-Clients, Playwright
│   └── api/             # Treibender Adapter: FastAPI-Router, Schemas, DI-Verdrahtung
├── Dockerfile           # python:3.11-slim → uvicorn :8000
├── docker-compose.yml   # lokaler Stack: redis + qdrant + core-api
├── requirements.txt
└── LICENSE              # MIT
```

Der Domänenkern hängt von nichts ab; die Außenwelt dockt über Ports an. Du kannst Qdrant,
die LLM-Engine oder das Web-Framework ersetzen, ohne die Geschäftslogik anzufassen.

### ⚡ Schnellstart

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # startet redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

Fertig — eine vollständige lokale KI-Engine unter `http://localhost:8000`.

</details>

---

<details>
<summary><h2>🇨🇳 中文</h2></summary>

### 🎯 项目愿景

**N-Assistant Core** 是一款**完全本地运行**的多智能体 AI 推理引擎。它将 **RAG（检索增强生成）**
大脑与由 **Playwright** 驱动的自动化臂膀融合在一起，使自治智能体能够自主研究、创作、审核并
**跨多渠道发布内容**，全程无需人工介入；除非*你*主动选择，否则不会向任何第三方云端发送一个字节。

它专为追求完全掌控的 AI 与 DevOps 工程师打造：随意更换 LLM、自主掌握向量索引、自托管整套技术
栈，并能审阅运行其中的每一行代码。

### 🏗️ 核心技术架构

| 支柱 | 作用 |
|---|---|
| **🔀 双引擎 LLM 路由** | 单一的 `LLMClientBase` 接口将推理路由到**离线**引擎（运行 Llama-3.1 / Qwen2.5 的 Ollama / Apple MLX）或**在线** API（OpenAI / Claude）。切换引擎只需修改一个配置项——无需改动代码。 |
| **🧠 多租户 & 多语言 RAG** | **Qdrant** 向量库 + **`BAAI/bge-m3`** 嵌入构建出统一的跨语言空间（越/英/德/中）。每一次 `upsert`/`search` 都通过强制的 `tenant_id` 负载过滤实现隔离。 |
| **🕹️ Supervisor–Worker 智能体模式** | 规划者（Planner）将意图分解为任务图；专职 Worker（研究员 → 创作者 → 评审 → 发布者）各自以最小上下文运行。评审者在内容发布前校验其事实依据。 |
| **📡 全渠道自动分发** | **Redis + Celery** 将异步任务下发给 **Playwright** 无头浏览器，模拟人类行为发布到各社交平台，以规避平台限流。 |

### 📂 目录结构（六边形架构）

```
n-assistant-core/
├── app/
│   ├── domain/          # 纯业务实体与端口——零框架依赖
│   ├── application/     # 用例：Supervisor-Worker 智能体编排
│   ├── infrastructure/  # 被驱动适配器：Qdrant、Redis/Celery、LLM 客户端、Playwright
│   └── api/             # 驱动适配器：FastAPI 路由、模式、依赖注入装配
├── Dockerfile           # python:3.11-slim → uvicorn :8000
├── docker-compose.yml   # 本地技术栈：redis + qdrant + core-api
├── requirements.txt
└── LICENSE              # MIT
```

领域核心不依赖任何东西；外部世界通过端口接入。你可以替换 Qdrant、LLM 引擎或 Web 框架，
而无需触碰任何业务逻辑。

### ⚡ 快速开始

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # 启动 redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

就这么简单——一个完整的本地 AI 引擎已运行在 `http://localhost:8000`。

</details>

---

<div align="center">

**License:** [MIT](LICENSE) · Free to use, modify, and self-host. Built for the open-source AI community. 🌍

</div>
