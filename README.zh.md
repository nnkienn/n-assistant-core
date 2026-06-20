<div align="center">

# Nyxara 🤖🚀

### 真正学会 AI 工程 — 从零搭建一个多语言 RAG + 智能体引擎，瞄准一个具体的细分领域

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)

**大多数"学 AI"的业余项目都死于把教程拼凑在一起——没有用户，也没法判断任何东西是否真的有效。Nyxara 押注相反的方向：你**亲手构建每一层**——高级 RAG、微调、智能体工作流、评估——并把它对准一个真实的任务：一个面向 TikTok Shop / Shopee 卖家联盟的*评论助手（Comment Assistant）*。人工介入审核（human-in-the-loop），绝不自动发布。**

🌐 🇬🇧 [English](./README.md) · 🇻🇳 [Tiếng Việt](./README.vi.md) · 🇩🇪 [Deutsch](./README.de.md) · 🇨🇳 **中文**

</div>

---

## 🎯 为什么有这个项目

有两件事杀死了大多数"我在学 AI 工程"的项目：

1. **它们是从教程缝起来的。** 你接好一个 LangChain retriever，得到一个答案，却从不明白*为什么*稠密检索会漏掉、RRF 究竟在算什么、你的 reranker 是否真的有用。理解从未真正沉淀。
2. **它们没有目的地。** 没有真实任务、没有真实用户、没法衡量"更好"。动力随之蒸发。

**Nyxara 同时解决这两点。** 它是一个你**从零构建**的多语言 **RAG + 智能体引擎**——掌握嵌入数学、RRF 公式、cross-encoder 重排、LoRA 更新、评估指标——并瞄准一个**有真实（即便很小）用户的具体细分领域：** 面向**越南 TikTok Shop / Shopee 卖家联盟**的内容与社媒自动化。

> **致读者：** 如果你想*理解* AI 工程——而不只是调用一个 API——通过构建一个有真实、可演示、可衡量目标的连贯系统来学习，那么这个仓库就是为你准备的。它**首先是一台学习载体**，其次才是一个细分工具。不是多租户 SaaS，不是市场博弈。

它默认**100% 本地运行**（除非你选择云端档，否则没有一个字节离开你的机器），一个 `tenant_id` **命名空间**让一次安装并排承载多个细分领域——*每个领域一个文件夹*，而非*每个付费客户一个租户*。没有计费、没有认证、没有面板。

---

## 🛍️ 旗舰用例 — 评论助手

这是让每一项技术都有存在理由的细分目的地。

一个卖家联盟在 TikTok Shop / Shopee 上发布一条产品视频。下方堆满了几十条评论：*"多少钱？"*、*"油皮能用吗？"*、*"发货要几天？"*。评论助手把这股洪流转化为经过审核、符合品牌口吻的回复：

1. **读取**视频下方的公开评论。
2. **检索**正确的产品事实——价格、成分、用法、官方链接——**过滤到*那个具体产品***（先做元数据过滤，*再*做语义检索——而不是"最近的向量获胜"）。
3. **起草**一条符合卖家口吻和语言的回复。
4. **审查：** 一个专门的**评论者（Critic）智能体拦截编造的事实和未经证实的功效宣称**——对美妆/健康类不可妥协，因为错误的宣称是信任与法律问题。
5. **人工审批**之后才发送。**Nyxara 绝不自动发布。** 当一条回复*被*发送时，它走平台的**官方 API**——绝不走隐身（stealth）浏览器。

下面每一项 RAG/智能体/评估技术，都通过在这里回答一个真实问题来证明自己的价值：*检索拉到正确的产品了吗？重排真的提升了答案吗？评论者抓住那条错误宣称了吗？*

---

## 🔥 核心能力

### 1. 🌾 可插拔采集器 — 任意平台，社区驱动
**这是第 0 阶段 — 一切其它东西赖以为生的基础。** 一个定时（cron）爬虫采集**公开**数据——为评论助手采集**产品信息和公开评论样本**——盖上 `tenant_id` 命名空间，落地到按领域划分的**原始数据湖**，再经过 3 层反垃圾过滤器清洗 — 与智能体完全解耦（*数据采集 ≠ 推理*；该层**绝不**调用 LLM）。

**接入任意平台 — 放入一个文件即可。** 引擎在运行时自动发现 [`extractors/plugins/`](./app/infrastructure/harvester/extractors/plugins/) 下的每个插件。新增数据源 = 写一个类 — 无需改动核心，无硬编码导入：

```python
class MyPlatformExtractor(BaseExtractor):
    PLUGIN_TYPE = "my_platform"          # ← 由 scraper_config.yaml 中的 `type:` 引用
    async def extract(self) -> list[HarvestedItem]:
        url = self.options["url"]        # 一切来自 YAML — 零硬编码
        ...
```

崩溃的插件会被记录并跳过 — 一个坏数据源绝不会拖垮整次运行。

**目前已交付：** `x_twscrape`（X / Twitter，经 twscrape）· `youtube_shorts`（YouTube Shorts，经 yt-dlp）。
**我们需要你的帮助** 🤝 — 公开站点的页面结构与速率限制时常变化。请贡献一个新平台插件（TikTok、Shopee、Instagram、Reddit…）或帮助让现有 extractor 保持**稳健且符合 ToS**。整个契约就在一个文件里：[`base.py`](./app/infrastructure/harvester/extractors/base.py)。

**3 层反垃圾过滤器** — 快速失败、成本敏感；每个条目必须挣得下一层，因此付费的 LLM 调用只会看到已经通过两道免费 CPU 关卡的内容：

| 层 | 阶段 | 成本 | 丢弃 |
|---|---|---|---|
| **L1** | 启发式（话题标签 / 词数 / @提及 阈值） | O(1) CPU | 互动诱饵、单行句、批量@提及垃圾 |
| **L2** | 文本清洗（去除 URL、表情、模板文字） | O(n) CPU | 清洗后为空的条目 |
| **L3** | LLM 评判（批量，OpenAI 兼容） | 约每 10 条 1 次 API 调用 | 笑话、回复、低价值闲聊 |

通过的条目落地到 `raw_data_lake/filtered/approved.json`，可直接入 Qdrant。数据源与阈值位于 [`scraper_config.yaml`](./scraper_config.yaml) → `filter_config`，**绝不硬编码**。

### 2. 🔀 双引擎 LLM 路由（本地 + 云）
单一的 `LLMClientBase`（OpenAI 兼容）接口让每个智能体在任一引擎上运行而**无需改代码**：
- **本地 / 开发档：** Ollama 或 Apple MLX 运行 `Qwen2.5` / `Llama-3.1-8B-Instruct` → 零成本研发，完全离线。
- **扩展档：** 租用 GPU（RunPod、AWS）上的 vLLM，或在重批量时回退到云 API。

路由是**运行时配置决策**，绝非重写。同一份智能体代码在两档上都能运行。

> **硬件预期（诚实）：** CORE 阶段在 CPU/无 GPU 机器上用本地 3B 模型即可舒适运行。但**评论者 / CRAG 评分**需要一个有能力的模型——在仅有 3B 的机器上，那种评判只是*尽力而为*，因此若你需要强力反幻觉，请把 Tier-1 路由到云/混合引擎。**可选的视觉引擎（ComfyUI 图像/视频 + TTS）需要真正的 GPU**，在 CPU-本地上不现实。"100% 本地"在 GPU 机器上端到端成立；在仅 CPU 的硬件上，它覆盖 RAG/智能体大脑，不包括可选的视觉分支。

### 3. 🧠 多细分领域 & 多语言 RAG
- **向量库：** [Qdrant](https://qdrant.tech/)，集合按命名空间隔离。
- **嵌入：** `BAAI/bge-m3`（1024 维，100+ 语言）→ 一个共享的跨语言索引，**无需每种语言一个集合**。
- **命名空间隔离：** 每次 `upsert` / `search` 都携带强制的 `tenant_id` 载荷过滤，因此多个领域在一个库中共存，**零跨领域渗漏** — 是架构保证，而非运行时检查。
- **跨语言检索：** 一个越南语领域可在同一空间中查询其德语知识库。
- **你在这里学到：** 分块策略、嵌入数学、手写余弦相似度，随后进入完整的**第 3 阶段高级 RAG 栈** — 混合检索、RRF、cross-encoder 重排、CRAG、查询变换，以及有度量的评估（见下方路线图）。

### 4. 🕹️ 主管–工作者 智能体拓扑
我们**不**把一切塞进一个巨型 prompt。每个请求被分解为专门角色：

| 角色 | 职责 | 工具 |
|---|---|---|
| **主管（规划者）** | 分解意图 → 有序任务图；路由到工作者 | 任务路由器 |
| **研究员** | 按命名空间的 RAG 查询（驱动第 3 阶段流水线） | `search_vector_db(tenant_id, …)` |
| **创作者** | 以卖家口吻起草回复 / 文案 | `generate_text` |
| **评论者** | 反幻觉：拦截编造事实与未经证实的功效宣称 | RAG 校验器（≤ 3 次重试循环） |
| **人工审核者** | 在发送前审批 / 编辑 / 拒绝 — **回路收束于一个人，而非自动发送** | 审核队列 |

**评论者是护城河**：它在草稿到达人之前校验依据，而人是最后一道闸门。**没有自动发布的智能体。** 当一条已审批的回复被发送时，它走平台的**官方 API**。

> 智能体图是插件形态：可选的视觉分支（更晚的阶段）可以加入 **视觉总监** 与 **视频制片** 节点，而不改变现有角色的契约。

---

## 🏗️ 六边形架构

领域核心不依赖任何东西；外部世界通过端口插入。你可以替换 Qdrant、LLM 引擎或 Web 框架而不触碰业务逻辑。

```
n-assistant-core/
├── app/
│   ├── domain/                  # 纯业务实体与端口 — 零框架依赖
│   ├── application/             # 用例 + 过滤流水线（3 层反垃圾）
│   ├── infrastructure/
│   │   └── harvester/           # engine.py · extractors/plugins/ (X, YouTube…) · filters/
│   └── api/                     # 驱动适配器：FastAPI 路由、schema、DI 装配
├── cli.py                       # ★ 统一 CLI — 所有采集操作的唯一入口
├── scraper_config.yaml          # 采集器数据源 + 过滤阈值 — 零硬编码
├── raw_data_lake/               # 按命名空间的落地区：texts/（原始）+ filtered/（清洗）
├── docker-compose.yml           # redis + qdrant + core-api（+ harvester profile）
├── Dockerfile · Dockerfile.harvester   # core-API 镜像 · 供插件用的 Chromium 镜像
├── requirements.txt
└── LICENSE                      # MIT
```

---

## ⚡ 技术栈

| 层 | 技术 |
|---|---|
| API | FastAPI (Python 3.11) · Pydantic v2 · SQLAlchemy 2.x |
| Vector / RAG | **Qdrant** · `BAAI/bge-m3` 嵌入（1024 维，多语言）· Hybrid + RRF + **cross-encoder 重排（`bge-reranker-v2-m3`）** + CRAG · 元数据过滤 · 语义分块 |
| 推理 | `LLMClientBase` → Ollama / Apple MLX（dev）· vLLM / Cloud API（scale） |
| 微调 | 在 `Qwen2.5-7B` 上做 LoRA · GGUF 量化合并（Q4/Q5/Q8）· 嵌入/领域微调 |
| 智能体框架 | LangGraph（主管–工作者，多智能体，人工介入） |
| 评估 | **RAGAS**（faithfulness、answer relevancy、context precision/recall）+ 自定义指标 + A/B 开关 — **自第 3 阶段起** |
| 异步任务 | Celery 5 + Redis 7 broker |
| MLOps（第 6 阶段） | LangFuse / Prometheus + Grafana · DVC / W&B / MLflow（轻量）· CI/CD 再训练 |
| 视觉 / 视频 — *可选* | ComfyUI · Flux / SDXL · ControlNet · IP-Adapter / FaceID · XTTS / CosyVoice · ffmpeg *(需 GPU)* |
| ML 运行时 | PyTorch（Mac 上 MPS，Linux GPU 上 CUDA） |
| 容器 | Docker Compose（profiles: default, harvester, rag） |
| 许可 | MIT |

---

## 🗺️ 路线图 — 一条学习路径

各阶段经过排序，每个阶段从零教授栈的一层。状态是诚实的，而非愿景。**CORE** 阶段是主学习路径；**可选（OPTIONAL）**的视觉分支位于一旁——架构允许你之后再把它装上，*而不*破坏已构建的部分，但它教的是扩散/视频，而非核心 AI 工程路线。

| 阶段 | 分支 | 主题 | 你构建 & 学到什么 | 状态 |
|---|---|---|---|---|
| **0. 基础** | CORE | 采集器：**产品数据 + 公开评论样本** · 干净的 MIT 仓库 · 按领域的示例 | 插件架构、零硬编码配置、3 层过滤器 | 🟢 完成 |
| **1. 骨架** | CORE | FastAPI 核心、`/health`、Docker、统一 CLI | 六边形架构、容器工作流 | ✅ 完成 |
| **2. 向量记忆** | CORE | 分块 + `bge-m3` + Qdrant + 多命名空间 | 嵌入数学、**手写**余弦相似度、命名空间隔离 | ✅ 完成 |
| **3. 高级 RAG + 评估** | CORE | 完整的检索大脑 — **见下方深入表格** — 加上内建的有度量评估（RAGAS + A/B） | RRF & 重排数学、查询↔文档空间、分块粒度、token 预算、图工作流、*度量每项技术是否有用* | ⏳ 进行中 |
| **4. 微调** | CORE | 在 `Qwen2.5-7B` 上做 **LoRA** · GGUF 合并 · 多领域数据集 · **嵌入/领域微调** | 低秩更新数学、量化、数据集与嵌入微调设计 | ⏳ 计划中 |
| **5. 智能体编排器** | CORE | LangGraph 主管–工作者（研究员 → 创作者 → **评论者**）· **评论助手** 端到端 · **人工介入审核** · 领域路由器 | 多智能体设计、依据与反幻觉、HITL 工作流、领域路由 | ⏳ 计划中 |
| **6. 生产、MLOps & 评估** | CORE | 完整 Docker 栈 · 监控/日志（LangFuse、Prometheus + Grafana）· `config.yaml` · CI/CD 再训练 · 实验跟踪（W&B / MLflow）· 版本管理（DVC / HF Hub） | 可观测性、可复现 ML、重型 MLOps | ⏳ 计划中 |
| **7. 社区与可扩展性** | CORE | 领域模板（卖家联盟、美妆、Tech…）· 插件架构（采集器 / LLM client）· 示例项目 | 开源可扩展性、插件设计 | ⏳ 计划中 |
| **★ 视觉与角色引擎** | **可选** | ComfyUI + IP-Adapter / FaceID + 角色 LoRA · Flux/SDXL + ControlNet · 图/文→视频 · 唇形同步 + TTS 克隆（XTTS/CosyVoice）· ffmpeg 自动剪辑 | 一致性技术、扩散控制、视频流水线 | 🧩 附加 · 需 GPU |

### 第 3 阶段深入 — 高级 RAG，每项技术按查询可开关

第 3 阶段的全部要点，就是**亲手**构建每一项技术（在 `LLMClientBase` + `qdrant-client` 之上用纯 Python，LangGraph 仅负责流程），然后**度量它是否真的有用** — *学 RAG 而不度量，就是盲学。*

| 技术 | 做什么 | 学到什么 |
|---|---|---|
| **混合检索**（dense + sparse/BM25） | 同时跑语义 + 关键词检索 | 何时 dense 胜 sparse、何时 sparse 胜 dense |
| **RRF**（Reciprocal Rank Fusion） | 把多个排名列表合并为一个 | 手写 RRF 公式；如何融合排名 |
| **Cross-encoder 重排**（`bge-reranker-v2-m3`，与 bge-m3 同族） | 通过*一起*读取 query+doc 来重新打分 top-k | 为什么重排在检索后对 top-k 质量提升最大；**bi-encoder vs cross-encoder** |
| **CRAG**（纠错式 RAG）经 LangGraph | 给检索到的上下文打分，再重试 / 扩展 / 升级 | 自评上下文；自我纠正的检索循环 |
| **查询变换**（Multi-Query + HyDE） | 在检索前扩展 / 改写查询 | 查询↔文档空间错配及其弥合 |
| **父子（small-to-big）检索** | 在小块上匹配，返回大的父块 | 精确匹配*且*完整上下文；分块粒度 |
| **上下文压缩** | 把检索块裁剪到只剩回答句子 | 削减噪声；小型本地 LLM 上的 token 预算管理 |
| **元数据过滤**（向量 + 过滤） | 在语义检索*之前*过滤到正确的产品 / 价格区间 | 结合结构化过滤 + 向量检索 — **在评论助手中实战使用** |
| **语义分块** | 按语义切分，而非固定长度 | 分块粒度如何塑造检索质量 |
| **评估**（RAGAS + 自定义 + A/B） | faithfulness、answer relevancy、context precision/recall | **重排 / CRAG / 改写是否真的改善** — 从"很久以后"提前到*现在* |

每项技术都是一个**按查询的 flag**，默认关闭，因此你可以 A/B *有* vs *无* 并读取指标。重型 MLOps（LangFuse/Prometheus/Grafana、CI/CD 再训练）留在第 6 阶段 — 只有**基础评估（RAGAS + A/B 对比）**提前到第 3 阶段。

### 你将深入学习的内容
- **数学：** 嵌入、余弦相似度、RRF、**cross-encoder 重排**、低秩适配（LoRA）、量化、**RAG 评估指标**。
- **架构：** 高级 RAG、智能体工作流（LangGraph）、向量数据库、多命名空间、人工介入。
- **生产：** 微调、量化、流水线编排、评估、轻量 MLOps。
- **工程：** 模块化代码、Docker、API 设计、开源最佳实践。
- **可选 / 视觉 AI：** ComfyUI 工作流、ControlNet、角色/身份一致性 *(若你在 GPU 机器上加上可选分支)*。

---

## 🚀 快速开始

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # 启动 redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

就是这样 — 一个完整的本地 AI 引擎运行在 `http://localhost:8000`。

| 服务 | URL |
|---|---|
| Core API (RAG / LLM) | http://localhost:8000 |
| Qdrant (向量库) | http://localhost:6333 |
| Redis (broker) | localhost:6379 |

📖 **[docs/HARVESTER_GUIDE.md](./docs/HARVESTER_GUIDE.md)** — 第 0 阶段深入：插件架构、CLI 参考、如何在 30 分钟内添加一个新爬虫。

**运行数据流水线** — 先采集再过滤，**完全通过 Docker**（无需本地 Python，无需 venv）。一个轻量包装脚本在 harvester 容器*内部*运行统一的 `cli.py`：

```bash
# Linux / macOS: ./nassistant.sh <命令>      Windows: .\nassistant.ps1 <命令>

# 显示所有已注册插件及其在 config/scraper_config.yaml 中的开/关状态
./nassistant.sh list-plugins

# 采集：抓取每个启用的数据源 → 原始数据湖
./nassistant.sh harvest

# 采集单个命名数据源（先 dry-run 预览）
./nassistant.sh harvest --source product-catalog-demo --dry-run
./nassistant.sh harvest --source product-catalog-demo

# 采集某一插件类型的全部数据源，每个限 5 条
./nassistant.sh harvest --type youtube_shorts --limit 5

# 过滤：对全部已采集数据运行 3 层反垃圾流水线
./nassistant.sh filter

# 仅过滤某一插件类型
./nassistant.sh filter --type youtube_shorts
```

运行 `./nassistant.sh --help` 或 `./nassistant.sh <命令> --help` 查看所有选项。

> **第 3 层调用 LLM**，因此先在 `.env` 中设置 `INFERENCE_PROVIDER` / `INFERENCE_BASE_URL` / `INFERENCE_MODEL` / `INFERENCE_API_KEY` — Gemini、OpenAI 或本地 Ollama（任何 OpenAI 兼容端点）。第 1–2 层仅用 CPU，无需密钥即可运行。

<details>
<summary>更喜欢原生 <code>docker compose</code>？（不用包装脚本）</summary>

包装脚本只是 `docker compose run` 的一行封装。harvester 镜像自带 `cli.py`，因此任何子命令都能用：

```bash
docker compose --profile harvester run --rm harvester python cli.py list-plugins
docker compose --profile harvester run --rm harvester python cli.py harvest
docker compose --profile harvester run --rm harvester python cli.py filter
```

</details>

---

## 🔐 不可妥协的工程规则

这些是**宪法级**的。违反它们的 PR 会被自动拒绝。

- 🛡️ **命名空间无处不在。** 每个向量库操作、缓存键和审计日志都必须携带 `tenant_id` 命名空间，使领域绝不互相渗漏。
- 🧠 **单一嵌入模型。** `BAAI/bge-m3` 是唯一允许的嵌入 — 无按语言的模型，无 OpenAI ada。
- 🔌 **`LLMClientBase` 抽象。** 智能体调用 `client.complete(...)` — 绝不直接调用 `openai.ChatCompletion.*` 或 `transformers`。
- ✅ **TDD 强制。** Red → Green → Refactor。RAG/智能体逻辑需要**跨语言测试**（VN、EN、DE、CN）。
- 🙋 **人工介入，不自动发布。** 草稿交给一个人审批、编辑或拒绝。任何东西都不会自动发送；当内容*被*发送时，它使用平台的**官方 API** — 绝不使用浏览器自动化 / 隐身发布。
- 🌾 **零硬编码采集。** 采集目标位于 `scraper_config.yaml`，仅公开页面，尊重 robots.txt。

---

<div align="center">

**许可：** [MIT](LICENSE) · 自由使用、fork、修改与自托管。为开源 AI 社区而建。🌍

📞 **nnkienn@gmail.com**

</div>
