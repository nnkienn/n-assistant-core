<div align="center">

# N-Assistant Core 🤖🚀

### 自治全渠道 AI 营销引擎

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)

**N Assistant 背后的 MIT 许可 AI 推理引擎——完全本地运行，无厂商锁定。**

🌐 🇬🇧 [English](./README.md) · 🇻🇳 [Tiếng Việt](./README.vi.md) · 🇩🇪 [Deutsch](./README.de.md) · 🇨🇳 **中文**

</div>

---

## 🎯 项目愿景

**N-Assistant Core** 是一款**完全本地运行**的多智能体 AI 推理引擎。

它将**多租户、多语言的 RAG（检索增强生成）**大脑与由 **Playwright** 驱动的自动化臂膀融合在一起，使自治智能体能够自主**研究 → 创作 → 审核 → 发布**内容，覆盖 TikTok、YouTube、Facebook 与 Instagram——全程无需人工介入；除非*你*主动选择，否则不会向任何第三方云端发送一个字节。

它专为追求完全掌控的 AI 与 DevOps 工程师打造：随意更换 LLM、自主掌握向量索引、自托管整套技术栈，并能审阅运行其中的每一行代码。

---

## 🔥 核心能力

### 1. 🔀 双引擎 LLM 路由（本地 + 云端）
单一的 `LLMClientBase` 接口（兼容 OpenAI）让每个智能体可在任一引擎上运行，**无需改动代码**：
- **本地 / 开发层：** Ollama 或 Apple MLX 运行 `Llama-3.1-8B-Instruct` / `Qwen2.5` → 零成本研发，完全离线。
- **生产 / 扩展层：** 在租用 GPU（RunPod、AWS）上运行 vLLM，或在高峰期回退到 OpenAI / Claude。

路由是**运行时配置决策**，绝非重写代码。同一份智能体代码可在两层上运行。

### 2. 🧠 多租户 & 多语言 RAG
- **向量库：** [Qdrant](https://qdrant.tech/)，采用按租户隔离的 collection。
- **嵌入：** `BAAI/bge-m3`（1024 维，100+ 语言）→ 一个共享的跨语言索引，**无需按语言建多个 collection**。
- **隔离：** 每一次 `upsert` / `search` 都强制施加 `tenant_id` 负载过滤。**零跨租户数据泄漏**是架构保证，而非运行时检查。
- **跨语言检索：** 越南语租户可在同一空间中查询其德语知识库。

### 3. 🕹️ Supervisor–Worker 智能体拓扑
我们**不会**把一切塞进一个巨型 prompt。每个请求都被分解为专职角色：

| 角色 | 职责 | 工具 |
|---|---|---|
| **Supervisor（规划者）** | 分解意图 → 有序任务图；路由到 Worker | 任务路由器 |
| **Researcher（研究员）** | 趋势挖掘 + 按租户的 RAG 查询 | `search_vector_db(tenant_id, …)` |
| **Creator（创作者）** | 撰写脚本 / 文案 / 分镜 | `generate_text`、`generate_image`、`generate_audio` |
| **Critic（评审）** | 品牌语调审核 + 防幻觉（论断 vs 上下文） | RAG 校验器（≤ 3 次重试循环） |
| **Publisher（发布者）** | 触发 Playwright 自动上传 | `publish_to_platform(tenant_id, …)` |

评审者在内容发布前校验其事实依据。

### 4. 📡 全渠道自动分发
**Redis + Celery** 将异步任务下发给 **Playwright** 无头浏览器，模拟人类行为发布内容，以规避平台限流：
- TikTok / 抖音 · YouTube Shorts · Facebook · Instagram Reels。
- 会话 Cookie 以 **AES-256 加密**存储（绝不明文）。
- 使用 `playwright-stealth` 规避机器人检测。
- 按租户时区 + 高峰时段启发式排程。

### 5. 🌾 自治采集器（Harvester）
定时（cron）运行的 **Playwright + Stealth** 爬虫，采集**公开**数据，清洗后带 `tenant_id` 写入 Qdrant——与智能体完全解耦（*数据采集 ≠ 推理*）。来源在 [`scraper_config.yaml`](./scraper_config.yaml) 中声明，**绝不硬编码**。

---

## 🏗️ 六边形架构

领域核心不依赖任何东西；外部世界通过端口接入。你可以替换 Qdrant、LLM 引擎或 Web 框架，而无需触碰任何业务逻辑。

```
n-assistant-core/
├── app/
│   ├── domain/          # 纯业务实体与端口——零框架依赖
│   ├── application/     # 用例：Supervisor-Worker 智能体编排
│   ├── infrastructure/  # 被驱动适配器：Qdrant · Redis/Celery · LLM 客户端 · Playwright 采集器
│   └── api/             # 驱动适配器：FastAPI 路由、模式、依赖注入装配
├── scraper_config.yaml  # 采集器数据源——零硬编码（Chặng 0）
├── docker-compose.yml   # 本地技术栈：redis + qdrant + core-api（+ harvester profile）
├── Dockerfile           # python:3.11-slim → uvicorn :8000
├── requirements.txt
└── LICENSE              # MIT
```

---

## ⚡ 技术栈

| 层 | 技术 |
|---|---|
| API | FastAPI（Python 3.11）· Pydantic v2 · SQLAlchemy 2.x |
| 向量 / RAG | **Qdrant** · `BAAI/bge-m3` 嵌入（1024 维，多语言） |
| 推理 | `LLMClientBase` → Ollama / Apple MLX（开发）· vLLM / 云端 API（生产） |
| 智能体框架 | LangGraph（Supervisor–Worker） |
| 异步任务 | Celery 5 + Redis 7 broker |
| 自动化 | Playwright + `playwright-stealth` |
| ML 运行时 | PyTorch（Mac 用 MPS，Linux GPU 用 CUDA） |
| 容器 | Docker Compose（profile：default、harvester） |
| 许可证 | MIT |

---

## 🗺️ 路线图

| 阶段 | 主题 | 状态 |
|---|---|---|
| **0. Harvester** | 自治公开数据采集（Playwright + Stealth，cron）→ Qdrant，与推理解耦 | 🟡 新增 |
| **2. Memory** | 基于 Qdrant + `bge-m3` 的 RAG、多语言入库管线、`tenant_id` 强制 | 🚧 进行中 |
| **3. Brain** | LLM 路由 + LangGraph Supervisor–Worker、Ollama/vLLM 双引擎、工具注册表 | ⏳ 下一步 |
| **4. Distribution** | Playwright 发布器、AES-256 会话保险库、高峰时段调度器 | ⏳ 计划中 |

---

## 🚀 快速开始

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # 启动 redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

就这么简单——一个完整的本地 AI 引擎已运行在 `http://localhost:8000`。

| 服务 | URL |
|---|---|
| Core API（RAG / LLM） | http://localhost:8000 |
| Qdrant（向量数据库） | http://localhost:6333 |
| Redis（broker） | localhost:6379 |

**启用 Harvester**（独立进程，cron 驱动）：

```bash
docker compose --profile harvester up -d
```

---

## 🔐 不可协商的工程规则

这些是**宪法级**规则。违反它们的 PR 会被自动拒绝。

- 🛡️ **`tenant_id` 无处不在。** 每一次向量数据库操作、每个缓存键、每条审计日志都必须携带 `tenant_id`。
- 🧠 **单一嵌入模型。** `BAAI/bge-m3` 是唯一允许的嵌入模型——不按语言建模型，不用 OpenAI ada。
- 🔌 **`LLMClientBase` 抽象。** 智能体调用 `client.complete(...)`——绝不直接调用 `openai.ChatCompletion.*` 或 `transformers`。
- ✅ **强制 TDD。** Red → Green → Refactor。RAG/智能体逻辑需要**跨语言测试**（越、英、德、中）。
- 🔒 **加密会话保险库。** Playwright Cookie → AES-256 → 存储。绝不明文。
- 🌾 **零硬编码采集。** 采集目标位于 `scraper_config.yaml`，仅限公开页面，遵守 robots.txt。

---

<div align="center">

**许可证：** [MIT](LICENSE) · 可自由使用、修改与自托管。为开源 AI 社区而打造。🌍

📞 **nnkienn@gmail.com**

</div>
