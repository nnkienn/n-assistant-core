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

它将**多租户、多语言的 RAG（检索增强生成）**大脑与由 **Playwright** 驱动的自动化臂膀融合在一起，使自治智能体能够自主**研究 → 创作 → 审核 → 发布**内容，覆盖 YouTube、Facebook 与 Instagram——全程无需人工介入；除非*你*主动选择，否则不会向任何第三方云端发送一个字节。

它专为追求完全掌控的 AI 与 DevOps 工程师打造：随意更换 LLM、自主掌握向量索引、自托管整套技术栈，并能审阅运行其中的每一行代码。

---

## 🔥 核心能力

### 1. 🌾 可插拔采集器（Harvester）—— 任意平台，社区共建
**这是阶段 0——其余一切赖以汲取数据的根基。** 定时（cron）爬虫采集**公开**数据，打上 `tenant_id`，落入按租户隔离的 **Raw Data Lake**，再经三层反垃圾过滤清洗——与智能体完全解耦（*数据采集 ≠ 推理*；本层**绝不**调用 LLM）。

**接入任意平台——只需放一个文件。** 引擎在运行时自动发现 [`extractors/plugins/`](./app/infrastructure/harvester/extractors/plugins/) 下的每个插件。新增一个来源就是写一个类——无需改动核心代码，无需硬编码导入：

```python
class MyPlatformExtractor(BaseExtractor):
    PLUGIN_TYPE = "my_platform"          # ← 由 scraper_config.yaml 中的 `type:` 引用
    async def extract(self) -> list[HarvestedItem]:
        url = self.options["url"]        # 一切皆取自 YAML —— 零硬编码
        ...
```

插件崩溃会被记录并跳过——一个坏来源绝不会拖垮整次运行。

**当前已内置：** `x_twscrape`（X / Twitter，经 twscrape）· `youtube_shorts`（YouTube Shorts，经 yt-dlp）。
**我们需要你的帮助** 🤝 —— 各平台的反爬虫机制持续演进。欢迎贡献新平台插件（TikTok、Instagram、Reddit、LinkedIn……）或为现有插件贡献新的 **绕过 / 隐身（bypass / stealth）技术**。整份契约只是一个文件：[`base.py`](./app/infrastructure/harvester/extractors/base.py)。

**三层反垃圾过滤**——快速失败、成本敏感；每个条目都必须"赢得"进入下一层的资格，因此付费的 LLM 调用只会看到已通过两道免费 CPU 关卡的内容：

| 层 | 阶段 | 成本 | 剔除 |
|---|---|---|---|
| **L1** | 启发式（hashtag / 词数 / @提及 阈值） | O(1) CPU | 互动诱饵、一句话、海量 @提及 垃圾 |
| **L2** | 文本清洗（去除 URL、表情、模板套话） | O(n) CPU | 清洗后为空的条目 |
| **L3** | LLM 评审（批量、兼容 OpenAI） | 每 10 条约 1 次 API 调用 | 玩笑、回复、低价值闲聊 |

通过的条目写入 `raw_data_lake/filtered/approved.json`，可直接入库 Qdrant。来源与阈值位于 [`scraper_config.yaml`](./scraper_config.yaml) → `filter_config`，**绝不硬编码**。

### 2. 🔀 双引擎 LLM 路由（本地 + 云端）
单一的 `LLMClientBase` 接口（兼容 OpenAI）让每个智能体可在任一引擎上运行，**无需改动代码**：
- **本地 / 开发层：** Ollama 或 Apple MLX 运行 `Llama-3.1-8B-Instruct` / `Qwen2.5` → 零成本研发，完全离线。
- **生产 / 扩展层：** 在租用 GPU（RunPod、AWS）上运行 vLLM，或在高峰期回退到 OpenAI / Claude。

路由是**运行时配置决策**，绝非重写代码。同一份智能体代码可在两层上运行。

### 3. 🧠 多租户 & 多语言 RAG
- **向量库：** [Qdrant](https://qdrant.tech/)，采用按租户隔离的 collection。
- **嵌入：** `BAAI/bge-m3`（1024 维，100+ 语言）→ 一个共享的跨语言索引，**无需按语言建多个 collection**。
- **隔离：** 每一次 `upsert` / `search` 都强制施加 `tenant_id` 负载过滤。**零跨租户数据泄漏**是架构保证，而非运行时检查。
- **跨语言检索：** 越南语租户可在同一空间中查询其德语知识库。

### 4. 🕹️ Supervisor–Worker 智能体拓扑
我们**不会**把一切塞进一个巨型 prompt。每个请求都被分解为专职角色：

| 角色 | 职责 | 工具 |
|---|---|---|
| **Supervisor（规划者）** | 分解意图 → 有序任务图；路由到 Worker | 任务路由器 |
| **Researcher（研究员）** | 趋势挖掘 + 按租户的 RAG 查询 | `search_vector_db(tenant_id, …)` |
| **Creator（创作者）** | 撰写脚本 / 文案 / 分镜 | `generate_text`、`generate_image`、`generate_audio` |
| **Critic（评审）** | 品牌语调审核 + 防幻觉（论断 vs 上下文） | RAG 校验器（≤ 3 次重试循环） |
| **Publisher（发布者）** | 触发 Playwright 自动上传 | `publish_to_platform(tenant_id, …)` |

评审者在内容发布前校验其事实依据。

### 5. 📡 全渠道自动分发
**Redis + Celery** 将异步任务下发给 **Playwright** 无头浏览器，模拟人类行为发布内容，以规避平台限流：
- YouTube Shorts · Facebook · Instagram Reels。
- 会话 Cookie 以 **AES-256 加密**存储（绝不明文）。
- 使用 `playwright-stealth` 规避机器人检测。
- 按租户时区 + 高峰时段启发式排程。

---

## 🏗️ 六边形架构

领域核心不依赖任何东西；外部世界通过端口接入。你可以替换 Qdrant、LLM 引擎或 Web 框架，而无需触碰任何业务逻辑。

```
n-assistant-core/
├── app/
│   ├── domain/                  # 纯业务实体与端口——零框架依赖
│   ├── application/             # 用例 + 过滤管线（三层反垃圾）
│   ├── infrastructure/
│   │   └── harvester/           # engine.py · extractors/plugins/（X、YouTube…）· filters/
│   └── api/                     # 驱动适配器：FastAPI 路由、模式、依赖注入装配
├── cli.py                       # ★ 统一 CLI —— 所有采集操作的唯一入口
├── scraper_config.yaml          # 采集器数据源 + 过滤阈值——零硬编码
├── raw_data_lake/               # 按租户落地区：texts/（原始）+ filtered/（清洗后）
├── docker-compose.yml           # redis + qdrant + core-api（+ harvester profile）
├── Dockerfile · Dockerfile.harvester   # core-API 镜像 · 供插件使用的 Chromium 镜像
├── requirements.txt
└── LICENSE                      # MIT
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

📖 **[docs/HARVESTER_GUIDE.md](./docs/HARVESTER_GUIDE.md)** —— 阶段 1 深入讲解：插件架构、CLI 参考、如何在 30 分钟内新增一个采集器。

**运行数据管线**——先采集再清洗，**全程通过 Docker**（无需本地 Python，无需 venv）。一个轻量 wrapper 脚本在 harvester 容器*内部*运行统一的 `cli.py`：

```bash
# Linux / macOS：./nassistant.sh <命令>      Windows：.\nassistant.ps1 <命令>

# 查看所有已注册插件 + 它们在 config/scraper_config.yaml 中的开/关状态
./nassistant.sh list-plugins

# 采集：抓取每个 enabled 来源 → Raw Data Lake
./nassistant.sh harvest

# 采集单个指定来源（先 dry-run 预览）
./nassistant.sh harvest --source yt-long-matt-wolfe --dry-run
./nassistant.sh harvest --source yt-long-matt-wolfe

# 采集某一插件类型的所有来源，每个来源上限 5 条
./nassistant.sh harvest --type youtube_long --limit 5

# 过滤：对所有已采集数据运行三层反垃圾管线
./nassistant.sh filter

# 仅过滤 YouTube Long Video 片段
./nassistant.sh filter --type youtube_long
```

运行 `./nassistant.sh --help` 或 `./nassistant.sh <命令> --help` 查看全部选项。

> **第 3 层会调用 LLM**，因此请先在 `.env` 中设置 `INFERENCE_PROVIDER` / `INFERENCE_BASE_URL` / `INFERENCE_MODEL` / `INFERENCE_API_KEY`——Gemini、OpenAI 或本地 Ollama（任何兼容 OpenAI 的端点）。第 1–2 层纯 CPU 运行，无需密钥。

<details>
<summary>更想用纯 <code>docker compose</code>？（不走 wrapper）</summary>

wrapper 只是 `docker compose run` 的一行封装。harvester 镜像内置 `cli.py`，因此任意子命令均可运行：

```bash
docker compose --profile harvester run --rm harvester python cli.py list-plugins
docker compose --profile harvester run --rm harvester python cli.py harvest
docker compose --profile harvester run --rm harvester python cli.py filter
```

</details>

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
