<div align="center">

# N-Assistant Core 🤖🚀

### Động cơ AI Marketing Tự hành Đa kênh

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Celery](https://img.shields.io/badge/Celery-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)

**Động cơ suy luận AI giấy phép MIT — nền tảng đứng sau N Assistant — chạy hoàn toàn local, không khóa nhà cung cấp.**

🌐 🇬🇧 [English](./README.md) · 🇻🇳 **Tiếng Việt** · 🇩🇪 [Deutsch](./README.de.md) · 🇨🇳 [中文](./README.zh.md)

</div>

---

## 🎯 Tầm nhìn dự án

**N-Assistant Core** là một động cơ suy luận AI đa agent được thiết kế để chạy **100% trên máy local**.

Nó kết hợp bộ não **RAG (Retrieval-Augmented Generation) đa người dùng, đa ngôn ngữ** với cánh tay tự động hóa điều khiển bằng **Playwright**, cho phép các agent tự hành **nghiên cứu → sáng tạo → kiểm duyệt → xuất bản** nội dung trên TikTok, YouTube, Facebook & Instagram — không cần con người can thiệp, và không gửi một byte dữ liệu nào lên cloud bên thứ ba trừ khi *bạn* muốn.

Dự án dành cho các kỹ sư AI và DevOps muốn toàn quyền kiểm soát: thay LLM tùy ý, sở hữu chỉ mục vector, tự host toàn bộ hệ thống, và đọc được từng dòng code đang chạy.

---

## 🔥 Năng lực Lõi

### 1. 🔀 Bộ định tuyến LLM Song Động cơ (Local + Cloud)
Một giao diện `LLMClientBase` duy nhất (tương thích OpenAI) cho phép mọi agent chạy trên engine nào cũng được mà **không cần sửa code**:
- **Tầng Local / Dev:** Ollama hoặc Apple MLX chạy `Llama-3.1-8B-Instruct` / `Qwen2.5` → R&D không tốn phí, hoàn toàn offline.
- **Tầng Production / Scale:** vLLM trên GPU thuê (RunPod, AWS) hoặc fallback sang OpenAI / Claude khi tải cao điểm.

Định tuyến là **quyết định cấu hình lúc runtime**, không phải viết lại code. Cùng một code agent chạy trên cả hai tầng.

### 2. 🧠 RAG Đa người dùng & Đa ngôn ngữ
- **Vector store:** [Qdrant](https://qdrant.tech/) với collection được cô lập theo tenant.
- **Embedding:** `BAAI/bge-m3` (1024 chiều, hơn 100 ngôn ngữ) → một chỉ mục xuyên ngôn ngữ chung, **không cần collection riêng cho từng ngôn ngữ**.
- **Cô lập:** mọi `upsert` / `search` đều bị ép qua bộ lọc payload `tenant_id` bắt buộc. **Zero rò rỉ chéo tenant** là một bảo đảm kiến trúc, không phải kiểm tra runtime.
- **Truy vấn xuyên ngôn ngữ:** một tenant tiếng Việt có thể truy vấn cơ sở tri thức tiếng Đức của họ trong cùng một không gian.

### 3. 🕹️ Topology Agent Supervisor–Worker
Chúng tôi **không** nhồi tất cả vào một prompt khổng lồ. Mỗi yêu cầu được phân rã thành các vai trò chuyên biệt:

| Vai trò | Trách nhiệm | Công cụ |
|---|---|---|
| **Supervisor (Planner)** | Phân rã ý định → đồ thị tác vụ có thứ tự; định tuyến tới worker | Task router |
| **Researcher** | Khai thác trend + truy vấn RAG theo tenant | `search_vector_db(tenant_id, …)` |
| **Creator** | Soạn script / copy / storyboard | `generate_text`, `generate_image`, `generate_audio` |
| **Critic** | Review brand-voice + chống ảo giác (claim-vs-context) | RAG verifier (≤ 3 vòng retry) |
| **Publisher** | Kích hoạt auto-upload qua Playwright | `publish_to_platform(tenant_id, …)` |

Critic kiểm chứng tính xác thực trước khi bất cứ thứ gì được xuất bản.

### 4. 📡 Tự động Phân phối Đa kênh
**Redis + Celery** rút hàng đợi tác vụ bất đồng bộ tới trình duyệt headless **Playwright** để đăng nội dung, mô phỏng hành vi người dùng để tránh giới hạn nền tảng:
- TikTok / Douyin · YouTube Shorts · Facebook · Instagram Reels.
- Cookie phiên được lưu **mã hóa AES-256** (không bao giờ plain-text).
- `playwright-stealth` để né phát hiện bot.
- Lên lịch theo múi giờ tenant + heuristic giờ vàng.

### 5. 🌾 Harvester Tự hành
Trình thu thập **Playwright + Stealth** chạy định kỳ (cron), cào dữ liệu **công khai**, làm sạch và nạp vào Qdrant kèm `tenant_id` — tách biệt hoàn toàn khỏi agent (*Thu thập dữ liệu ≠ Suy luận*). Nguồn khai báo trong [`scraper_config.yaml`](./scraper_config.yaml), **không hardcode**.

---

## 🏗️ Kiến trúc Hexagonal

Lõi domain không phụ thuộc gì cả; thế giới bên ngoài cắm vào qua các port. Bạn có thể thay Qdrant, engine LLM hay web framework mà không cần động đến logic nghiệp vụ.

```
n-assistant-core/
├── app/
│   ├── domain/          # Thực thể nghiệp vụ thuần & port — không phụ thuộc framework
│   ├── application/     # Use case: điều phối agent Supervisor-Worker
│   ├── infrastructure/  # Adapter bị điều khiển: Qdrant · Redis/Celery · LLM client · Playwright Harvester
│   └── api/             # Adapter điều khiển: router FastAPI, schema, nối DI
├── scraper_config.yaml  # Nguồn cào của Harvester — zero-hardcode (Chặng 0)
├── docker-compose.yml   # Stack local: redis + qdrant + core-api (+ profile harvester)
├── Dockerfile           # python:3.11-slim → uvicorn :8000
├── requirements.txt
└── LICENSE              # MIT
```

---

## ⚡ Ngăn xếp công nghệ

| Tầng | Công nghệ |
|---|---|
| API | FastAPI (Python 3.11) · Pydantic v2 · SQLAlchemy 2.x |
| Vector / RAG | **Qdrant** · embedding `BAAI/bge-m3` (1024 chiều, đa ngôn ngữ) |
| Suy luận | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud API (prod) |
| Agent framework | LangGraph (Supervisor–Worker) |
| Tác vụ async | Celery 5 + broker Redis 7 |
| Tự động hóa | Playwright + `playwright-stealth` |
| ML runtime | PyTorch (MPS trên Mac, CUDA trên GPU Linux) |
| Container | Docker Compose (profile: default, harvester) |
| Giấy phép | MIT |

---

## 🗺️ Lộ trình

| Chặng | Chủ đề | Trạng thái |
|---|---|---|
| **0. Harvester** | Thu thập dữ liệu công khai tự hành (Playwright + Stealth, cron) → Qdrant, tách khỏi suy luận | 🟡 Mới |
| **2. Memory** | RAG trên Qdrant + `bge-m3`, pipeline nạp đa ngôn ngữ, ép buộc `tenant_id` | 🚧 Đang làm |
| **3. Brain** | Router LLM + LangGraph Supervisor–Worker, song động cơ Ollama/vLLM, tool registry | ⏳ Tiếp theo |
| **4. Distribution** | Publisher Playwright, két phiên AES-256, scheduler giờ vàng | ⏳ Dự kiến |

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

**Bật Harvester** (tiến trình riêng, chạy theo cron):

```bash
docker compose --profile harvester up -d
```

---

## 🔐 Quy tắc Kỹ thuật Bất di Bất dịch

Đây là các quy tắc **hiến định**. PR vi phạm sẽ bị tự động từ chối.

- 🛡️ **`tenant_id` ở khắp nơi.** Mọi thao tác Vector DB, cache key và audit log đều PHẢI mang `tenant_id`.
- 🧠 **Một model embedding duy nhất.** `BAAI/bge-m3` là embedding duy nhất được phép — không model riêng theo ngôn ngữ, không OpenAI ada.
- 🔌 **Trừu tượng `LLMClientBase`.** Agent gọi `client.complete(...)` — không bao giờ gọi trực tiếp `openai.ChatCompletion.*` hay `transformers`.
- ✅ **TDD bắt buộc.** Red → Green → Refactor. Logic RAG/Agent cần **test xuyên ngôn ngữ** (VN, EN, DE, CN).
- 🧱 **Ranh giới Open-Core.** Repo này **không bao giờ** được import Stripe hay UI quản trị tenant.
- 🔒 **Két phiên mã hóa.** Cookie Playwright → AES-256 → lưu trữ. Không bao giờ plain-text.
- 🌾 **Cào dữ liệu zero-hardcode.** Mục tiêu cào nằm trong `scraper_config.yaml`, chỉ trang công khai, tôn trọng robots.txt.

---

<div align="center">

**Giấy phép:** [MIT](LICENSE) · Tự do sử dụng, chỉnh sửa và tự host. Xây cho cộng đồng AI mã nguồn mở. 🌍

📞 **nnkienn@gmail.com**

</div>
