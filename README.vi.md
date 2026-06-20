<div align="center">

# Nyxara 🤖🚀

### Học AI engineering thật — tự build động cơ RAG đa ngôn ngữ + agentic từ đầu, hướng tới một ngách cụ thể

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)

**Phần lớn dự án "học AI" chết yểu vì là một mớ tutorial ghép lại, không có người dùng và không có cách nào biết thứ mình làm có chạy đúng không. Nyxara đặt cược ngược lại: bạn **tự tay xây từng tầng** — RAG nâng cao, fine-tuning, agentic, evaluation — và hướng nó vào một công việc thật: một *Comment Assistant* cho seller-affiliate TikTok Shop / Shopee. Có người duyệt (human-in-the-loop), KHÔNG bao giờ tự đăng.**

🌐 🇬🇧 [English](./README.md) · 🇻🇳 **Tiếng Việt** · 🇩🇪 [Deutsch](./README.de.md) · 🇨🇳 [中文](./README.zh.md)

</div>

---

## 🎯 Vì sao có dự án này

Hai thứ giết chết hầu hết dự án "tôi đang học AI engineering":

1. **Chúng được khâu từ tutorial.** Bạn ráp một retriever LangChain, ra được câu trả lời, nhưng không bao giờ hiểu *vì sao* dense retrieval trượt, RRF thực sự tính cái gì, hay reranker có giúp ích không. Sự hiểu biết không bao giờ đọng lại.
2. **Chúng không có đích đến.** Không tác vụ thật, không người dùng thật, không cách nào đo "tốt hơn". Động lực bốc hơi.

**Nyxara sửa cả hai.** Đây là một động cơ **RAG + agentic đa ngôn ngữ mà bạn tự build từ đầu** — sở hữu toán embedding, công thức RRF, cross-encoder rerank, cập nhật LoRA, các chỉ số eval — và nó hướng tới một **ngách cụ thể có người dùng thật (dù nhỏ):** tự động hóa content & social cho **seller-affiliate trên TikTok Shop / Shopee tại Việt Nam.**

> **Dành cho người đọc:** nếu bạn muốn *hiểu* AI engineering — không chỉ gọi một API — bằng cách build một hệ thống mạch lạc với đích thật mà bạn có thể demo và đo lường, thì repo này dành cho bạn. Đây trước hết là một **cỗ máy để học**, sau đó mới là một công cụ ngách. Không phải SaaS đa người dùng, không phải canh bạc thị trường.

Nó chạy **100% local** mặc định (không byte nào rời máy bạn trừ khi bạn chọn tầng cloud), và một `tenant_id` **namespace** cho phép một bản cài chứa nhiều niche song song — *một folder cho mỗi niche*, không phải *một tenant cho mỗi khách trả tiền*. Không thu phí, không auth, không dashboard.

---

## 🛍️ Sản phẩm-lõi đầu tiên — Comment Assistant

Đây là đích ngách khiến mọi kỹ thuật có lý do tồn tại.

Một seller-affiliate đăng video bán hàng lên TikTok Shop / Shopee. Bên dưới, hàng chục comment dồn về: *"giá bao nhiêu?"*, *"da dầu dùng được không?"*, *"ship mấy ngày?"*. Comment Assistant biến cơn lũ đó thành các câu trả lời đúng giọng, đã được duyệt:

1. **Đọc** comment công khai dưới video.
2. **Truy xuất** đúng thông tin sản phẩm — giá, thành phần, công dụng, link chính thức — **lọc đúng *sản phẩm đó*** (lọc metadata trước, *rồi mới* semantic search — không phải "vector gần nhất thắng").
3. **Soạn** câu trả lời đúng giọng và đúng ngôn ngữ của seller.
4. **Phê bình:** một **Critic agent chặn thông tin bịa và claim công dụng chưa kiểm chứng** — bất di bất dịch với mỹ phẩm/sức khỏe, nơi một claim sai là vấn đề niềm tin và pháp lý.
5. **Người duyệt** trước khi bất cứ thứ gì được gửi. **Nyxara không bao giờ tự đăng.** Khi một câu trả lời *thật sự* được gửi, nó đi qua **API chính thức** của nền tảng — không bao giờ qua trình duyệt lén (stealth).

Mọi kỹ thuật RAG/agent/eval bên dưới đều giành được chỗ đứng bằng cách trả lời một câu hỏi thật ở đây: *retrieval có lấy đúng sản phẩm không? rerank có thật sự nâng câu trả lời không? Critic có bắt được claim sai không?*

---

## 🔥 Năng lực Lõi

### 1. 🌾 Harvester Cắm-được — Nền tảng bất kỳ, Cộng đồng cùng xây
**Đây là Chặng 0 — nền móng mà mọi thứ khác ăn dữ liệu từ đó.** Trình thu thập chạy định kỳ (cron) cào dữ liệu **công khai** — **thông tin sản phẩm và mẫu comment công khai** phục vụ Comment Assistant — đóng dấu namespace `tenant_id`, đổ vào **Raw Data Lake** tách theo từng niche, rồi làm sạch qua bộ lọc chống spam 3 lớp — tách biệt hoàn toàn khỏi agent (*Thu thập dữ liệu ≠ Suy luận*; tầng này **không bao giờ** gọi LLM).

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
**Rất cần bạn góp sức** 🤝 — các trang public liên tục đổi markup và rate-limit. Hãy đóng góp plugin nền tảng mới (TikTok, Shopee, Instagram, Reddit…) hoặc giúp giữ một extractor hiện có **ổn định và tuân thủ ToS**. Toàn bộ hợp đồng gói gọn trong một file: [`base.py`](./app/infrastructure/harvester/extractors/base.py).

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

> **Kỳ vọng phần cứng (thành thật):** các chặng CORE chạy thoải mái trên máy CPU/không GPU với model 3B local. Nhưng **Critic / chấm điểm CRAG** cần một model đủ mạnh — trên máy chỉ-3B việc chấm đó là *best-effort*, nên hãy định tuyến Tier-1 sang engine cloud/hybrid nếu bạn cần chống ảo giác mạnh. **Visual Engine TÙY CHỌN (ComfyUI image/video + TTS) cần GPU thật** và không thực tế khi chạy CPU-local. "100% local" đúng từ đầu đến cuối trên máy GPU; trên phần cứng chỉ-CPU nó bao trùm bộ não RAG/agent, không bao gồm nhánh visual tùy chọn.

### 3. 🧠 RAG Đa niche & Đa ngôn ngữ
- **Vector store:** [Qdrant](https://qdrant.tech/) với collection cô lập theo namespace.
- **Embedding:** `BAAI/bge-m3` (1024 chiều, hơn 100 ngôn ngữ) → một chỉ mục xuyên ngôn ngữ chung, **không cần collection riêng cho từng ngôn ngữ**.
- **Cô lập namespace:** mọi `upsert` / `search` đều mang bộ lọc payload `tenant_id` bắt buộc, nên nhiều niche cùng tồn tại trong một store với **zero lẫn dữ liệu chéo niche** — một bảo đảm kiến trúc, không phải kiểm tra runtime.
- **Truy vấn xuyên ngôn ngữ:** một niche tiếng Việt có thể truy vấn cơ sở tri thức tiếng Đức của nó trong cùng một không gian.
- **Bạn học gì ở đây:** chiến lược chunking, toán embedding, tự tay code cosine similarity, rồi tới **toàn bộ stack RAG nâng cao của Chặng 3** — Hybrid Search, RRF, cross-encoder reranking, CRAG, query transformation, và evaluation có đo lường (xem roadmap bên dưới).

### 4. 🕹️ Topology Agent Supervisor–Worker
Chúng tôi **không** nhồi tất cả vào một prompt khổng lồ. Mỗi yêu cầu được phân rã thành các vai trò chuyên biệt:

| Vai trò | Trách nhiệm | Công cụ |
|---|---|---|
| **Supervisor (Planner)** | Phân rã ý định → đồ thị tác vụ có thứ tự; định tuyến tới worker | Task router |
| **Researcher** | Truy vấn RAG theo namespace (điều khiển pipeline Chặng 3) | `search_vector_db(tenant_id, …)` |
| **Creator** | Soạn câu trả lời / copy đúng giọng seller | `generate_text` |
| **Critic** | Chống ảo giác: chặn thông tin bịa & claim công dụng chưa kiểm chứng | RAG verifier (≤ 3 vòng retry) |
| **Người duyệt (Human Reviewer)** | Duyệt / sửa / từ chối trước khi gửi — **vòng lặp khép lại ở một con người, không phải ở auto-gửi** | Hàng đợi duyệt |

**Critic là hào nước**: nó kiểm chứng tính xác thực trước khi bản nháp tới tay người duyệt, và con người là cổng cuối cùng. **Không có agent tự-đăng-bài.** Khi một câu trả lời đã duyệt được gửi, nó đi qua **API chính thức** của nền tảng.

> Đồ thị agent có dạng plugin: nhánh Visual TÙY CHỌN (Chặng sau) có thể thêm node **Visual Director** và **Video Producer** mà không thay đổi hợp đồng của các vai trò hiện có.

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
| Vector / RAG | **Qdrant** · embedding `BAAI/bge-m3` (1024 chiều, đa ngôn ngữ) · Hybrid + RRF + **cross-encoder rerank (`bge-reranker-v2-m3`)** + CRAG · lọc metadata · semantic chunking |
| Suy luận | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud API (scale) |
| Fine-tuning | LoRA trên `Qwen2.5-7B` · merge lượng tử hóa GGUF (Q4/Q5/Q8) · fine-tune embedding/domain |
| Agent framework | LangGraph (Supervisor–Worker, multi-agent, human-in-the-loop) |
| Eval | **RAGAS** (faithfulness, answer relevancy, context precision/recall) + custom metrics + bật/tắt A/B — **từ Chặng 3** |
| Tác vụ async | Celery 5 + broker Redis 7 |
| MLOps (Chặng 6) | LangFuse / Prometheus + Grafana · DVC / W&B / MLflow (nhẹ) · CI/CD retrain |
| Hình ảnh / Video — *TÙY CHỌN* | ComfyUI · Flux / SDXL · ControlNet · IP-Adapter / FaceID · XTTS / CosyVoice · ffmpeg *(cần GPU)* |
| ML runtime | PyTorch (MPS trên Mac, CUDA trên GPU Linux) |
| Container | Docker Compose (profile: default, harvester, rag) |
| Giấy phép | MIT |

---

## 🗺️ Lộ trình — Một Con đường Học

Các chặng được sắp xếp để mỗi chặng dạy bạn một tầng của hệ thống từ đầu. Trạng thái là thật, không phải mơ ước. Các chặng **CORE** là con đường học chính; nhánh **OPTIONAL** Visual nằm bên lề — kiến trúc cho phép bạn lắp thêm sau mà *không* phá phần đã build, nhưng nó dạy diffusion/video, không phải con đường AI-engineering cốt lõi.

| Chặng | Nhánh | Chủ đề | Bạn xây & học gì | Trạng thái |
|---|---|---|---|---|
| **0. Nền móng** | CORE | Harvester: **dữ liệu sản phẩm + mẫu comment công khai** · repo MIT sạch · ví dụ theo niche | Kiến trúc plugin, config zero-hardcode, bộ lọc 3 lớp | 🟢 Xong |
| **1. Khung xương** | CORE | FastAPI core, `/health`, Docker, CLI thống nhất | Kiến trúc Hexagonal, quy trình container | ✅ Xong |
| **2. Bộ nhớ Vector** | CORE | Chunking + `bge-m3` + Qdrant + đa namespace | Toán embedding, **tự tay** code cosine similarity, cô lập namespace | ✅ Xong |
| **3. RAG Nâng cao + Eval** | CORE | Bộ não retrieval đầy đủ — **xem bảng chi tiết bên dưới** — kèm evaluation có đo lường (RAGAS + A/B) tích hợp sẵn | Toán RRF & rerank, không gian query↔doc, độ mịn chunk, quản lý token budget, graph workflow, *đo xem mỗi kỹ thuật có giúp ích không* | ⏳ Đang làm |
| **4. Fine-tuning** | CORE | **LoRA** trên `Qwen2.5-7B` · merge GGUF · dataset đa domain · **fine-tune embedding/domain** | Toán cập nhật low-rank, lượng tử hóa, thiết kế dataset & tinh chỉnh embedding | ⏳ Dự kiến |
| **5. Agentic Orchestrator** | CORE | LangGraph Supervisor–Worker (Researcher → Creator → **Critic**) · **Comment Assistant** end-to-end · **người duyệt (human-in-the-loop)** · domain router | Thiết kế multi-agent, grounding & chống ảo giác, quy trình HITL, định tuyến theo niche | ⏳ Dự kiến |
| **6. Production, MLOps & Eval** | CORE | Full Docker stack · monitoring/logging (LangFuse, Prometheus + Grafana) · `config.yaml` · CI/CD retrain · experiment tracking (W&B / MLflow) · versioning (DVC / HF Hub) | Observability, ML tái lập được, MLOps nặng | ⏳ Dự kiến |
| **7. Cộng đồng & Mở rộng** | CORE | Template niche (seller-affiliate, beauty, tech…) · kiến trúc plugin (scraper / LLM client) · dự án ví dụ | Khả năng mở rộng OSS, thiết kế plugin | ⏳ Dự kiến |
| **★ Visual & Character Engine** | **OPTIONAL** | ComfyUI + IP-Adapter / FaceID + character LoRA · Flux/SDXL + ControlNet · image/text→video · lip-sync + TTS clone (XTTS/CosyVoice) · ffmpeg auto-edit | Kỹ thuật nhất quán, điều khiển diffusion, pipeline video | 🧩 Add-on · cần GPU |

### Chặng 3 chi tiết — RAG nâng cao, mọi kỹ thuật bật/tắt theo từng query

Cốt lõi của Chặng 3 là tự tay build từng kỹ thuật **bằng tay** (pure Python trên `LLMClientBase` + `qdrant-client`, LangGraph chỉ lo flow) rồi **đo xem nó có thật sự giúp ích không** — *học RAG mà không đo là học mù.*

| Kỹ thuật | Làm gì | Học được gì |
|---|---|---|
| **Hybrid Search** (dense + sparse/BM25) | chạy retrieval semantic + từ khóa cùng lúc | khi nào dense thắng sparse và khi nào sparse thắng dense |
| **RRF** (Reciprocal Rank Fusion) | gộp nhiều bảng xếp hạng thành một | công thức RRF bằng tay; cách gộp các bảng xếp hạng |
| **Cross-encoder reranking** (`bge-reranker-v2-m3`, cùng họ bge-m3) | chấm lại top-k bằng cách đọc query+doc *cùng nhau* | vì sao rerank nâng chất lượng top-k mạnh nhất sau retrieval; **bi-encoder vs cross-encoder** |
| **CRAG** (Corrective RAG) qua LangGraph | chấm điểm context truy xuất rồi retry / mở rộng / escalate | tự chấm điểm context; vòng lặp retrieval tự sửa |
| **Query Transformation** (Multi-Query + HyDE) | mở rộng / viết lại truy vấn trước khi search | lệch không gian query↔document và cách thu hẹp |
| **Parent-Child** (small-to-big) retrieval | match trên chunk nhỏ, trả về khối parent lớn | match chính xác *và* đủ context; độ mịn chunk |
| **Context Compression** | cắt chunk truy xuất chỉ còn câu trả lời | cắt nhiễu; quản lý token budget trên LLM local nhỏ |
| **Metadata filtering** (vector + filter) | lọc đúng sản phẩm / khoảng giá *trước* semantic search | kết hợp lọc cấu trúc + vector search — **dùng thật trong Comment Assistant** |
| **Semantic chunking** | cắt theo ngữ nghĩa, không theo độ dài cố định | độ mịn chunk định hình chất lượng retrieval thế nào |
| **Evaluation** (RAGAS + custom + A/B) | faithfulness, answer relevancy, context precision/recall | **rerank / CRAG / rewrite có thật sự cải thiện không** — kéo từ "tận sau này" lên *bây giờ* |

Mỗi kỹ thuật là một **flag theo từng query**, mặc định tắt, nên bạn có thể A/B *có* vs *không* và đọc số liệu. MLOps nặng (LangFuse/Prometheus/Grafana, CI/CD retrain) vẫn ở Chặng 6 — chỉ **eval cơ bản (RAGAS + so sánh A/B)** được kéo lên Chặng 3.

### Những thứ bạn sẽ học sâu
- **Toán học:** embedding, cosine similarity, RRF, **cross-encoder reranking**, low-rank adaptation (LoRA), lượng tử hóa, **các chỉ số đánh giá RAG**.
- **Kiến trúc:** RAG nâng cao, agentic workflow (LangGraph), vector DB, đa namespace, human-in-the-loop.
- **Production:** fine-tuning, lượng tử hóa, điều phối pipeline, đánh giá, MLOps nhẹ.
- **Kỹ thuật:** code modular, Docker, thiết kế API, best practice mã nguồn mở.
- **Tùy chọn / Visual AI:** ComfyUI workflows, ControlNet, nhất quán nhân vật/danh tính *(nếu bạn thêm nhánh tùy chọn trên máy GPU)*.

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
./nassistant.sh harvest --source product-catalog-demo --dry-run
./nassistant.sh harvest --source product-catalog-demo

# Cào tất cả nguồn của một loại plugin, giới hạn 5 item mỗi nguồn
./nassistant.sh harvest --type youtube_shorts --limit 5

# Lọc: chạy pipeline chống spam 3 lớp trên toàn bộ dữ liệu thô
./nassistant.sh filter

# Lọc chỉ một loại plugin
./nassistant.sh filter --type youtube_shorts
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

- 🛡️ **Namespace ở khắp nơi.** Mọi thao tác Vector DB, cache key và audit log đều PHẢI mang namespace `tenant_id` để các niche không bao giờ lẫn vào nhau.
- 🧠 **Một model embedding duy nhất.** `BAAI/bge-m3` là embedding duy nhất được phép — không model riêng theo ngôn ngữ, không OpenAI ada.
- 🔌 **Trừu tượng `LLMClientBase`.** Agent gọi `client.complete(...)` — không bao giờ gọi trực tiếp `openai.ChatCompletion.*` hay `transformers`.
- ✅ **TDD bắt buộc.** Red → Green → Refactor. Logic RAG/Agent cần **test xuyên ngôn ngữ** (VN, EN, DE, CN).
- 🙋 **Human-in-the-loop, không auto-đăng.** Bản nháp tới tay một con người để duyệt, sửa, hoặc từ chối. Không gì được gửi tự động; khi nội dung *thật sự* được gửi, nó dùng **API chính thức** của nền tảng — không bao giờ tự động hóa trình duyệt / đăng lén.
- 🌾 **Cào dữ liệu zero-hardcode.** Mục tiêu cào nằm trong `scraper_config.yaml`, chỉ trang công khai, tôn trọng robots.txt.

---

<div align="center">

**Giấy phép:** [MIT](LICENSE) · Tự do sử dụng, fork, chỉnh sửa và tự host. Xây cho cộng đồng AI mã nguồn mở. 🌍

📞 **nnkienn@gmail.com**

</div>
