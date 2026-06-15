<div align="center">

# N-Assistant Core 🤖🚀

### Nhà máy Nội dung Ảo Mã nguồn Mở — fork cho niche của bạn, chạy 100% local

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)

**Một động cơ giấy phép MIT, modular, để dựng pipeline nội dung AI tự hành — cào → ghi nhớ → suy luận → fine-tune → tạo hình ảnh → xuất bản. Chạy hoàn toàn local, không khóa nhà cung cấp.**

🌐 🇬🇧 [English](./README.md) · 🇻🇳 **Tiếng Việt** · 🇩🇪 [Deutsch](./README.de.md) · 🇨🇳 [中文](./README.zh.md)

</div>

---

## 🎯 Tầm nhìn dự án

**N-Assistant Core** là một **Nhà máy Nội dung Ảo** mã nguồn mở: một động cơ AI modular mà bạn **fork và tùy chỉnh cho chính niche của mình** — MMO/affiliate, Game AI, Beauty, Crypto, Giáo dục, bất cứ thứ gì — và chạy **100% trên máy local**.

Nó nối bộ não **RAG (Retrieval-Augmented Generation) đa ngôn ngữ** với đồ thị agent **LangGraph** và cánh tay tự động hóa **Playwright**, để một pipeline tự hành có thể **nghiên cứu → viết → tạo hình ảnh → kiểm duyệt → xuất bản** nội dung trên YouTube, Facebook & Instagram — không cần con người can thiệp, và không gửi một byte nào lên cloud bên thứ ba trừ khi *bạn* muốn.

Đây là một **cỗ máy để học sâu, không phải sản phẩm để bán.** Mục tiêu là *hiểu* từng tầng — toán embedding, RRF, cập nhật low-rank của LoRA, lượng tử hóa, đồ thị agent, kỹ thuật nhất quán của ComfyUI — bằng cách tự tay xây từ đầu và sở hữu từng dòng code đang chạy.

> **Đa niche, không phải SaaS đa người dùng.** Một bản cài có thể chứa nhiều niche song song. Một `tenant_id` (namespace) giữ tri thức của mỗi niche tách biệt trong vector store — chỉ mục MMO không bao giờ lẫn vào chỉ mục Game AI. **Không thu phí, không auth, không cloud thương mại** — chỉ là một namespace sạch để bạn (hoặc một fork) chạy nhiều domain từ một động cơ.

---

## 🔥 Năng lực Lõi

### 1. 🌾 Harvester Cắm-được — Nền tảng bất kỳ, Cộng đồng cùng xây
**Đây là Chặng 0 — nền móng mà mọi thứ khác ăn dữ liệu từ đó.** Trình thu thập chạy định kỳ (cron) cào dữ liệu **công khai**, đóng dấu namespace `tenant_id`, đổ vào **Raw Data Lake** tách theo từng niche, rồi làm sạch qua bộ lọc chống spam 3 lớp — tách biệt hoàn toàn khỏi agent (*Thu thập dữ liệu ≠ Suy luận*; tầng này **không bao giờ** gọi LLM).

**Cắm nền tảng bất kỳ — chỉ cần thả 1 file.** Engine tự động phát hiện mọi plugin trong [`extractors/plugins/`](./app/infrastructure/harvester/extractors/plugins/) lúc runtime. Thêm một nguồn = viết một class — không sửa code lõi, không import hardcode:

```python
class MyPlatformExtractor(BaseExtractor):
    PLUGIN_TYPE = "my_platform"          # ← tham chiếu qua `type:` trong scraper_config.yaml
    async def extract(self) -> list[HarvestedItem]:
        url = self.options["url"]        # mọi thứ lấy từ YAML — zero-hardcode
        ...
```

Plugin lỗi sẽ được log và bỏ qua — một nguồn hỏng không bao giờ kéo sập cả lượt chạy.

**Hiện đã có:** `x_twscrape` (X / Twitter qua twscrape) · `youtube_shorts` (YouTube Shorts qua yt-dlp).
**Rất cần bạn góp sức** 🤝 — các nền tảng liên tục thay đổi cơ chế chống bot. Hãy đóng góp plugin nền tảng mới (TikTok, Instagram, Reddit, LinkedIn…) hoặc một **kỹ thuật by-pass / stealth** mới cho plugin hiện có. Toàn bộ hợp đồng gói gọn trong một file: [`base.py`](./app/infrastructure/harvester/extractors/base.py).

**Bộ lọc chống spam 3 lớp** — dừng sớm và tiết kiệm chi phí; mỗi item phải "giành" được lớp kế tiếp, nên lời gọi LLM tốn tiền chỉ thấy thứ đã vượt qua 2 cổng CPU miễn phí:

| Lớp | Giai đoạn | Chi phí | Loại bỏ |
|---|---|---|---|
| **L1** | Heuristic (ngưỡng hashtag / số từ / mention) | O(1) CPU | mồi tương tác, câu cụt, spam mass-mention |
| **L2** | Text-clean (bỏ URL, emoji, rác lặp) | O(n) CPU | item rỗng sau khi làm sạch |
| **L3** | LLM judge (theo batch, OpenAI-compat) | ~1 lời gọi API / 10 item | câu đùa, reply, nội dung giá trị thấp |

Item đạt được ghi vào `raw_data_lake/filtered/approved.json`, sẵn sàng nạp Qdrant. Nguồn và ngưỡng lọc nằm trong [`scraper_config.yaml`](./scraper_config.yaml) → `filter_config`, **không hardcode**.

### 2. 🔀 Bộ định tuyến LLM Song Động cơ (Local + Cloud)
Một giao diện `LLMClientBase` duy nhất (tương thích OpenAI) cho phép mọi agent chạy trên engine nào cũng được mà **không cần sửa code**:
- **Tầng Local / Dev:** Ollama hoặc Apple MLX chạy `Qwen2.5` / `Llama-3.1-8B-Instruct` → R&D không tốn phí, hoàn toàn offline.
- **Tầng Scale:** vLLM trên GPU thuê (RunPod, AWS) hoặc fallback sang cloud API khi chạy batch nặng.

Định tuyến là **quyết định cấu hình lúc runtime**, không phải viết lại code. Cùng một code agent chạy trên cả hai tầng.

### 3. 🧠 RAG Đa niche & Đa ngôn ngữ
- **Vector store:** [Qdrant](https://qdrant.tech/) với collection cô lập theo namespace.
- **Embedding:** `BAAI/bge-m3` (1024 chiều, hơn 100 ngôn ngữ) → một chỉ mục xuyên ngôn ngữ chung, **không cần collection riêng cho từng ngôn ngữ**.
- **Cô lập namespace:** mọi `upsert` / `search` đều mang bộ lọc payload `tenant_id` bắt buộc, nên nhiều niche/user cùng tồn tại trong một store với **zero lẫn dữ liệu chéo niche** — một bảo đảm kiến trúc, không phải kiểm tra runtime.
- **Truy vấn xuyên ngôn ngữ:** một niche tiếng Việt có thể truy vấn cơ sở tri thức tiếng Đức của nó trong cùng một không gian.
- **Bạn học gì ở đây:** chiến lược chunking, toán embedding, tự tay code cosine similarity, rồi **Hybrid Search + RRF + Corrective RAG (CRAG)** khi bộ não trưởng thành hơn (Chặng 3).

### 4. 🕹️ Topology Agent Supervisor–Worker
Chúng tôi **không** nhồi tất cả vào một prompt khổng lồ. Mỗi yêu cầu được phân rã thành các vai trò chuyên biệt:

| Vai trò | Trách nhiệm | Công cụ |
|---|---|---|
| **Supervisor (Planner)** | Phân rã ý định → đồ thị tác vụ có thứ tự; định tuyến tới worker | Task router |
| **Researcher** | Khai thác trend + truy vấn RAG theo namespace | `search_vector_db(tenant_id, …)` |
| **Creator** | Soạn script / copy / storyboard | `generate_text`, `generate_image`, `generate_audio` |
| **Critic** | Review giọng điệu + chống ảo giác (claim-vs-context) | RAG verifier (≤ 3 vòng retry) |
| **Publisher** | Kích hoạt auto-upload qua Playwright | `publish_to_platform(tenant_id, …)` |

Critic kiểm chứng tính xác thực trước khi bất cứ thứ gì được xuất bản. Khi **Visual Engine** xuất hiện (Chặng 5–6), đồ thị này mọc thêm **Visual Director** và **Video Producer**.

### 5. 📡 Tự động Phân phối Đa kênh
**Redis + Celery** rút hàng đợi tác vụ bất đồng bộ tới trình duyệt headless **Playwright** để đăng nội dung, mô phỏng hành vi người dùng để tránh giới hạn nền tảng:
- YouTube Shorts · Facebook · Instagram Reels.
- Cookie phiên được lưu **mã hóa AES-256** (không bao giờ plain-text).
- `playwright-stealth` để né phát hiện bot.
- Lên lịch theo múi giờ namespace + heuristic giờ vàng.

---

## 🏗️ Kiến trúc Hexagonal

Lõi domain không phụ thuộc gì cả; thế giới bên ngoài cắm vào qua các port. Bạn có thể thay Qdrant, engine LLM hay web framework mà không cần động đến logic nghiệp vụ.

```
n-assistant-core/
├── app/
│   ├── domain/                  # Thực thể nghiệp vụ thuần & port — không phụ thuộc framework
│   ├── application/             # Use case + các filter pipeline (chống spam 3 lớp)
│   ├── infrastructure/
│   │   └── harvester/           # engine.py · extractors/plugins/ (X, YouTube…) · filters/
│   └── api/                     # Adapter điều khiển: router FastAPI, schema, nối DI
├── cli.py                       # ★ CLI thống nhất — điểm vào duy nhất cho mọi thao tác cào
├── scraper_config.yaml          # Nguồn cào + ngưỡng lọc của Harvester — zero-hardcode
├── raw_data_lake/               # Vùng đổ theo namespace: texts/ (thô) + filtered/ (sạch)
├── docker-compose.yml           # redis + qdrant + core-api (+ profile harvester)
├── Dockerfile · Dockerfile.harvester   # image core-API · image Chromium cho plugin
├── requirements.txt
└── LICENSE                      # MIT
```

---

## ⚡ Ngăn xếp công nghệ

| Tầng | Công nghệ |
|---|---|
| API | FastAPI (Python 3.11) · Pydantic v2 · SQLAlchemy 2.x |
| Vector / RAG | **Qdrant** · embedding `BAAI/bge-m3` (1024 chiều, đa ngôn ngữ) · Hybrid + RRF + CRAG |
| Suy luận | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud API (scale) |
| Fine-tuning | LoRA trên `Qwen2.5-7B` · merge lượng tử hóa GGUF (Q4/Q5/Q8) |
| Hình ảnh / Video | ComfyUI · Flux / SDXL · ControlNet · IP-Adapter / FaceID · XTTS / CosyVoice · ffmpeg |
| Agent framework | LangGraph (Supervisor–Worker, multi-agent) |
| Tác vụ async | Celery 5 + broker Redis 7 |
| Tự động hóa | Playwright + `playwright-stealth` |
| Eval / MLOps | RAGAS + custom metrics · LangFuse / Prometheus + Grafana · DVC / W&B / MLflow (nhẹ) |
| ML runtime | PyTorch (MPS trên Mac, CUDA trên GPU Linux) |
| Container | Docker Compose (profile: default, harvester, rag) |
| Giấy phép | MIT |

---

## 🗺️ Lộ trình — Một Con đường Học, Chặng 0→8

Các chặng được sắp xếp để mỗi chặng dạy bạn một tầng của hệ thống từ đầu. Trạng thái là thật, không phải mơ ước.

| Chặng | Chủ đề | Bạn xây & học gì | Trạng thái |
|---|---|---|---|
| **0. Nền móng** | Pipeline cào dữ liệu (JSON thô từ X, YouTube, web) · repo MIT sạch · ví dụ theo niche | Kiến trúc plugin, config zero-hardcode, bộ lọc 3 lớp | 🟢 Xong |
| **1. Khung xương** | FastAPI core, `/health`, Docker, CLI thống nhất | Kiến trúc Hexagonal, quy trình container | ✅ Xong |
| **2. Bộ nhớ Vector** | Chunking + `bge-m3` + Qdrant + đa namespace | Toán embedding, **tự tay** code cosine similarity, cô lập namespace | ✅ Xong |
| **3. RAG Nâng cao** | Hybrid Search + **RRF** + **Corrective RAG (CRAG)** qua LangGraph · domain adapter theo niche | Toán RRF, graph workflow, sửa lỗi retrieval | ⏳ Tiếp theo |
| **4. Fine-tuning** | **LoRA** trên `Qwen2.5-7B` · dataset đa domain (base + theo niche) · merge GGUF | Toán cập nhật low-rank, lượng tử hóa, thiết kế dataset | ⏳ Dự kiến |
| **5. Visual & Character Engine** | ComfyUI + IP-Adapter / FaceID + character LoRA · Flux/SDXL + ControlNet · image/text→video · lip-sync + TTS clone (XTTS/CosyVoice) · ffmpeg auto-edit | Kỹ thuật nhất quán, điều khiển diffusion, pipeline video | ⏳ Dự kiến |
| **6. Agentic Orchestrator** | LangGraph multi-agent (Researcher → Script Writer → Visual Director → Video Producer → Critic) · **domain router** · tool calling | Thiết kế multi-agent, định tuyến theo niche | ⏳ Dự kiến |
| **7. Production, MLOps & Eval** | Full Docker stack (Qdrant + Ollama + ComfyUI + FastAPI + Redis) · **RAGAS** + custom metrics · monitoring/logging (LangFuse, Prometheus + Grafana) · `config.yaml` · CI/CD retrain · experiment tracking (W&B / MLflow) · versioning dataset/adapter/prompt (DVC / HF Hub) | Framework eval, observability, MLOps nhẹ | ⏳ Dự kiến |
| **8. Cộng đồng & Mở rộng** | Template niche (MMO, Game AI, Tech, Giáo dục…) · kiến trúc plugin (scraper / visual / TTS) · dự án ví dụ | Khả năng mở rộng OSS, thiết kế plugin | ⏳ Dự kiến |

### Những thứ bạn sẽ học sâu
- **Toán học:** embedding, cosine similarity, RRF, low-rank adaptation (LoRA), lượng tử hóa.
- **Kiến trúc:** RAG nâng cao, agentic workflow (LangGraph), vector DB, đa namespace.
- **Production:** fine-tuning, lượng tử hóa, điều phối pipeline, đánh giá, MLOps nhẹ.
- **Visual AI:** ComfyUI workflows, ControlNet, nhất quán nhân vật/danh tính.
- **Kỹ thuật:** code modular, Docker, thiết kế API, best practice mã nguồn mở.

---

## 🚀 Bắt đầu nhanh

```bash
git clone https://github.com/nnkienn/n-assistant-core.git
cd n-assistant-core
docker compose up -d          # khởi chạy redis + qdrant + core-api

curl http://localhost:8000/health
# {"status":"ok","service":"core-api-opensource"}
```

Vậy là xong — một động cơ AI local hoàn chỉnh tại `http://localhost:8000`.

| Dịch vụ | URL |
|---|---|
| Core API (RAG / LLM) | http://localhost:8000 |
| Qdrant (vector DB) | http://localhost:6333 |
| Redis (broker) | localhost:6379 |

📖 **[docs/HARVESTER_GUIDE.vi.md](./docs/HARVESTER_GUIDE.vi.md)** ([English](./docs/HARVESTER_GUIDE.md)) — Hướng dẫn chuyên sâu Chặng 0: kiến trúc plugin, tham chiếu CLI, cách thêm scraper mới trong 30 phút.

**Chạy pipeline dữ liệu** — cào rồi lọc, **hoàn toàn qua Docker** (không cần Python local, không cần venv). Một script wrapper mỏng chạy `cli.py` thống nhất *bên trong* container harvester:

```bash
# Linux / macOS: ./nassistant.sh <lệnh>      Windows: .\nassistant.ps1 <lệnh>

# Xem tất cả plugin đã đăng ký + trạng thái bật/tắt trong config/scraper_config.yaml
./nassistant.sh list-plugins

# Cào: quét mọi nguồn enabled → Raw Data Lake
./nassistant.sh harvest

# Cào một nguồn cụ thể (thử dry-run trước để preview)
./nassistant.sh harvest --source yt-long-matt-wolfe --dry-run
./nassistant.sh harvest --source yt-long-matt-wolfe

# Cào tất cả nguồn của một loại plugin, giới hạn 5 item mỗi nguồn
./nassistant.sh harvest --type youtube_long --limit 5

# Lọc: chạy pipeline chống spam 3 lớp trên toàn bộ dữ liệu thô
./nassistant.sh filter

# Lọc chỉ các đoạn transcript YouTube Long Video
./nassistant.sh filter --type youtube_long
```

Chạy `./nassistant.sh --help` hoặc `./nassistant.sh <lệnh> --help` để xem toàn bộ tùy chọn.

> **Lớp 3 gọi LLM**, nên đặt trước `INFERENCE_PROVIDER` / `INFERENCE_BASE_URL` / `INFERENCE_MODEL` / `INFERENCE_API_KEY` trong `.env` — Gemini, OpenAI, hoặc Ollama local (bất kỳ endpoint tương thích OpenAI). Lớp 1–2 chỉ dùng CPU, chạy được mà không cần key.

<details>
<summary>Muốn dùng <code>docker compose</code> thuần? (không qua wrapper)</summary>

Wrapper chỉ là một dòng lệnh bọc quanh `docker compose run`. Image harvester có sẵn `cli.py`, nên mọi lệnh con đều chạy được:

```bash
docker compose --profile harvester run --rm harvester python cli.py list-plugins
docker compose --profile harvester run --rm harvester python cli.py harvest
docker compose --profile harvester run --rm harvester python cli.py filter
```

</details>

---

## 🔐 Quy tắc Kỹ thuật Bất di Bất dịch

Đây là các quy tắc **hiến định**. PR vi phạm sẽ bị tự động từ chối.

- 🛡️ **Namespace ở khắp nơi.** Mọi thao tác Vector DB, cache key và audit log đều PHẢI mang namespace `tenant_id` để các niche/user không bao giờ lẫn vào nhau.
- 🧠 **Một model embedding duy nhất.** `BAAI/bge-m3` là embedding duy nhất được phép — không model riêng theo ngôn ngữ, không OpenAI ada.
- 🔌 **Trừu tượng `LLMClientBase`.** Agent gọi `client.complete(...)` — không bao giờ gọi trực tiếp `openai.ChatCompletion.*` hay `transformers`.
- ✅ **TDD bắt buộc.** Red → Green → Refactor. Logic RAG/Agent cần **test xuyên ngôn ngữ** (VN, EN, DE, CN).
- 🔒 **Két phiên mã hóa.** Cookie Playwright → AES-256 → lưu trữ. Không bao giờ plain-text.
- 🌾 **Cào dữ liệu zero-hardcode.** Mục tiêu cào nằm trong `scraper_config.yaml`, chỉ trang công khai, tôn trọng robots.txt.

---

<div align="center">

**Giấy phép:** [MIT](LICENSE) · Tự do sử dụng, fork, chỉnh sửa và tự host. Xây cho cộng đồng AI mã nguồn mở. 🌍

📞 **nnkienn@gmail.com**

</div>
