# 🗺️ MASTER EXECUTION PLAN — N Assistant Core (V3.0, engine scope)

> **Scope:** the **open-source engine** roadmap for `n-assistant-core`. This is the
> core-repo view of the canonical plan; the full project plan (including the
> commercial Monetization stage) lives in the `n-assistant-cloud` copy.
> **Companion docs:** [`product-requirements.md`](product-requirements.md) ·
> [`ai-agent-design.md`](ai-agent-design.md) ·
> [`../rules/tech-stack-rule.md`](../rules/tech-stack-rule.md).

---

## Engine stages

| Chặng | Theme | Status |
|---|---|---|
| **Chặng 0** | **Harvester Engine** — autonomous data acquisition (Playwright + Stealth, cron) → Qdrant | 🟡 **NEW (V3.0)** |
| **Chặng 1** | Foundation — FastAPI core, health, Docker, project skeleton | ✅ Done |
| **Chặng 2** | Vector Memory / RAG — **Qdrant** + `bge-m3`, multilingual ingest, `tenant_id` enforcement | 🟡 In planning |
| **Chặng 3** | Autonomous brain — LangGraph Supervisor-Worker, dual-engine LLM router, tool registry | ⚪ TODO |
| **Chặng 4** | Omnichannel distribution — Playwright auto-upload, AES-256 session vault, scheduler | ⚪ TODO |

> Productization / billing stages are out of scope for this open-source repo and
> live in the commercial layer. The engine exposes APIs; it never implements billing.

---

## Chặng 0 — Harvester Engine (NEW in V3.0)

> **Goal:** an autonomous, scheduled subsystem that acquires **public** data and
> lands it — cleaned and `tenant_id`-tagged — into Qdrant, **without any LLM in the
> loop**. See [`product-requirements.md` §3.8](product-requirements.md).
> **Principle:** *Data Ingestion ≠ Inference.* The Harvester never calls an agent.

### Workstream

1. **Playwright harvester module** (`app/infrastructure/harvester/`) — headless
   Playwright + `playwright-stealth`. **Zero-hardcode:** all targets from
   `scraper_config.yaml` (URL, selectors, cadence, locale, `tenant_id`).
2. **Proxy rotation** — per-tenant residential proxy pool; rotate on block; backoff on 429/403.
3. **Cron scheduling** — Celery Beat per-source `cadence`.
4. **Clean-ingestion pipeline** — Crawl → Raw Data Lake (immutable, tagged) →
   Filter (boilerplate strip, dedupe, PII scrub, language detect) → `bge-m3` →
   **Qdrant upsert** with mandatory `tenant_id` payload filter.
5. **Harvester REST API** (`/v1/harvester/*`) — list/add/remove sources, trigger run, status.

### Compliance gates

- Public-data-only; no other-tenant PII; respect `robots.txt` / ToS.
- `tenant_id` stamped on the **raw** artifact at harvest time; missing → discarded.
- Cross-language ingest test (VN/EN/DE/CN) proving `tenant_id` isolation.

### Definition of done

- `docker compose up` starts a `harvester` service that reads `scraper_config.yaml`,
  crawls a configured public sample, and a `tenant_id`-filtered Qdrant query returns
  the harvested chunks. No hardcoded URLs anywhere.



# 🌍 ĐẶC TẢ KIẾN TRÚC TỔNG THỂ TOÀN CẦU — N ASSISTANT V3.0 (PHIÊN BẢN ZERO-HARDCODE)

> **Nhật ký cập nhật V3.0 (Zero-Hardcode & Tích hợp Harvester toàn diện):** Bổ sung §3.8 Tầng Máy Gặt - Harvester (thu thập dữ liệu tự động, tách biệt hoàn toàn với quá trình suy luận của AI); chốt **Qdrant** là cơ sở dữ liệu vector duy nhất; Lộ trình thực thi chính thức được chuyển sang file `master-execution-plan.md` với **Chặng 0 — Động cơ Harvester** mới.
> **PHÂN LOẠI TÀI LIỆU:** Đặc tả kỹ thuật cốt lõi. Bắt buộc tuân thủ đối với mọi AI Agent và lập trình viên tham gia dự án.
> **TẦM NHÌN DỰ ÁN:** N Assistant là một Nền tảng B2B SaaS AI Marketing đa người dùng (Multi-tenant) theo mô hình "Open-Core". Ba cam kết kiến trúc lõi: (1) Cách ly dữ liệu khách hàng tuyệt đối qua RAG gắn `tenant_id`, (2) Suy luận kết hợp Dual-Engine (Máy cục bộ + Đám mây), (3) Tự động đăng tải đa kênh qua Playwright.
> **NGÔN NGỮ HỖ TRỢ TOÀN DIỆN:** Tiếng Việt (VN), Tiếng Anh (EN), Tiếng Đức (DE), Tiếng Trung (CN).

---

## §0. TẦM NHÌN CHIẾN LƯỢC TOÀN CẦU (System Prompts)

Tiêm (Inject) dòng prompt phù hợp với ngôn ngữ vào ngữ cảnh gốc của mọi AI Agent khi làm việc:

* 🇻🇳 **Tiếng Việt:** N Assistant là nền tảng B2B SaaS AI Marketing tự hành đa người dùng (Multi-tenant). Cốt lõi: RAG bảo mật tuyệt đối theo `tenant_id`, suy luận Hybrid (Local/Cloud), và phân phối nội dung đa nền tảng.
* 🇬🇧 **Tiếng Anh:** N Assistant is a Multi-tenant B2B SaaS AI Marketing Agent. The core is an isolated RAG system, hybrid inference routing (Local Open-Source vs Cloud API), and omnichannel auto-upload.
* 🇩🇪 **Tiếng Đức:** N Assistant ist eine mandantenfähige B2B-SaaS-Plattform für KI-Marketing. Kernfunktionen: datenschutzkonformes RAG (DSGVO), hybride KI-Inferenz und automatisierte Omnichannel-Verteilung.
* 🇨🇳 **Tiếng Trung:** N Assistant 是一款多租户 B2B SaaS AI 营销自动化平台，核心优势：严格隔离的 RAG 知识库、混合大模型推理架构、全渠道自动发布工作流。

---

## §1. CHIẾN LƯỢC MÃ NGUỒN — Hai Repo Open-Core

| Kho lưu trữ (Repo) | Giấy phép | Tech Stack | Chứa những gì |
| --- | --- | --- | --- |
| **`n-assistant-core`** | MIT (Công khai) | Python 3.11 · FastAPI · LangGraph · Qdrant · Playwright · PyTorch | Trái tim điều phối AI, luồng RAG, kịch bản Agent, robot tự đăng bài. Chạy qua Docker, native trên Mac M4, hoặc GPU tự host. |
| **`n-assistant-cloud`** | Thương mại (Nội bộ) | TypeScript · Next.js 15 · Tailwind v4 · Stripe · PostgreSQL · Auth | Dashboard SaaS đa người dùng, thanh toán, quản lý quyền, ví `TenantCredits`, nhật ký hệ thống. Gọi `core` qua REST/WebSocket. |

**Giao kèo ranh giới (bắt buộc kiểm tra qua CI):**

* Bản `core` TUYỆT ĐỐI KHÔNG import Stripe, UI quản lý khách hàng, hay logic tính tiền.
* Bản `cloud` TUYỆT ĐỐI KHÔNG tự viết lại Agent hay gọi trực tiếp tới mô hình AI.
* Hai bên **chỉ** giao tiếp qua REST/WebSocket API.

---

## §2. LUỒNG DỮ LIỆU ĐA NGÔN NGỮ

```mermaid
graph TD
    Client[Next.js Client UI · i18n VN/EN/DE/CN] -->|JWT { user_id, tenant_id, role, locale }| API_Gateway[Cloud API / Auth]
    API_Gateway -->|REST + WebSocket| FastAPI[FastAPI Orchestrator · Supervisor]
    FastAPI <--> Postgres[(PostgreSQL · Người dùng · Thanh toán · Cấu hình)]
    FastAPI -->|Tác vụ Async| RedisQueue[(Redis Queue)]
    RedisQueue --> CeleryWorker[Celery Workers]

    CeleryWorker <-->|lọc theo tenant_id| EmbeddingModel[BAAI/bge-m3 Embedding đa ngôn ngữ]
    EmbeddingModel <--> VectorDB[(Qdrant · Cách ly tuyệt đối theo tenant_id)]

    CeleryWorker <-->|LLMClientBase| LLMRouter{Định tuyến LLM Dual-Engine}
    LLMRouter -->|Cấp độ 1: Đám mây (Prod)| CloudLLM[vLLM trên Cloud GPU · hoặc OpenAI fallback]
    LLMRouter -->|Cấp độ 2: Nội bộ (Dev/Local)| LocalLLM[Ollama / Apple MLX · Llama-3.1-8B / Hermes 3 / Qwen2.5]

    CeleryWorker -->|Kích hoạt tự đăng bài| PlaywrightBot[Trình duyệt ảo Playwright]
    PlaywrightBot --> YouTube[YouTube Shorts]
    PlaywrightBot --> Facebook[FB / IG Reels]

```

---

## §3. CHI TIẾT CÁC TẦNG KIẾN TRÚC

### §3.1 Tầng Ứng dụng & i18n

* **Framework:** Next.js 15 (App Router).
* **Giao diện:** Tailwind v4 + Shadcn UI (phong cách `radix-nova`).
* **Đa ngôn ngữ (i18n):** Sử dụng `next-intl` với các file `vi.json` / `en.json` / `de.json` / `zh.json`.
* **Quản lý trạng thái:** React Query (cache máy chủ) + Zustand (trạng thái UI nhánh client).
* **Xác thực:** Passkey + OAuth. Dữ liệu JWT **BẮT BUỘC** phải chứa `{ user_id, tenant_id, role, locale }`. Thiếu bất kỳ trường nào → middleware từ chối ngay lập tức.

### §3.2 Tầng Điều phối (Orchestration Layer)

* **Framework:** Python FastAPI, Kiến trúc Hexagonal (`app/domain`, `app/application`, `app/infrastructure`, `app/api`).
* **Trách nhiệm:** Nhận request từ UI, chia nhỏ tài liệu, điều khiển luồng Agent (Supervisor-Worker) bằng LangGraph.
* **Bảo mật:** Trình xác thực `tenant_id` (chặn nếu không khớp với tài nguyên), rate-limit theo từng tenant.
* **Luật thép (Zero-Hardcode):** Khi `INFERENCE_MODE=self_hosted`, hệ thống **KHÔNG ĐƯỢC** gọi bất kỳ API HTTPS nào ra ngoài (như OpenAI/Anthropic). CI sẽ chặn điều này.

### §3.3 Tầng RAG Đa người dùng

* **Vector DB:** Qdrant.
* **Hào nước cách ly (Moat):** Bắt buộc phải có bộ lọc `tenant_id` trên mọi truy vấn `upsert` và `search`. Việc truy vấn chéo dữ liệu giữa các tenant là vi phạm kiến trúc nghiêm trọng.
* **Luồng xử lý:** LangChain text splitters → Nhúng bằng `BAAI/bge-m3` → Đưa vào Qdrant với metadata `{tenant_id, doc_id, source, locale, ingested_at}`.
* **Khả năng xuyên ngôn ngữ:** Mô hình `bge-m3` tạo ra một không gian vector dùng chung cho VN/EN/DE/CN. Khách hàng Việt Nam có thể tra cứu tài liệu tiếng Đức của họ mà không cần dịch trước.

### §3.4 Tầng Suy luận AI Song động cơ (Tuyệt đối Không Hardcode)

Sử dụng một interface duy nhất tương thích OpenAI là `LLMClientBase`. Cho phép các Agent đổi não bộ qua file cấu hình mà không đụng chạm đến code.

```python
class LLMClientBase(Protocol):
    async def complete(self, *, messages: list[Message], tools: list[Tool] | None = None, max_tokens: int) -> Completion: ...

```

| Cấp độ | Tình huống sử dụng | Triển khai thực tế |
| --- | --- | --- |
| **Local / Dev** | R&D không tốn phí, dùng offline, bảo mật 100% | Ollama (`:11434`) hoặc Apple MLX phục vụ `Hermes 3` / `Llama-3.1-8B` |
| **Production / Scale** | Xử lý tải SaaS lớn | vLLM trên Cloud GPU, hoặc OpenAI / Claude 3.5 làm dự phòng lúc cao điểm |

Quyết định định tuyến hoàn toàn dựa vào file cấu hình (ví dụ: `INFERENCE_MODE=local|cloud|hybrid`), không viết thẳng vào code. Đoạn code logic của Agent giữ nguyên bất kể chạy ở cấp độ nào.

### §3.5 Tầng Phân phối Đa kênh (Playwright)

* **Cốt lõi:** Playwright (trình duyệt không giao diện) giả lập hành vi con người để vượt qua giới hạn API của các nền tảng mạng xã hội.
* **Két sắt phiên làm việc (Session Vault):** Cookie của Facebook, YouTube... được mã hóa **AES-256** và lưu trong PostgreSQL. **Tuyệt đối không lưu plain-text.**
* **Vượt rào Bot:** Sử dụng `playwright-stealth` và thay đổi proxy (IP dân cư) theo từng tenant.

### §3.6 Tầng Tác vụ Bất đồng bộ & Thu phí

* **Công nhân:** Redis broker + Celery xử lý mọi tác vụ kéo dài >2s (Đọc PDF, upload video...).
* **Thu phí:** Webhooks của Stripe (**chỉ nằm ở repo Cloud**).
* **Theo dõi Token:** Đếm token đầu vào/ra của từng lệnh gọi LLM, trừ tiền trực tiếp vào ví `TenantCredits` theo thời gian thực. Hết tiền -> Agent dừng hoạt động.

### §3.7 Tầng Quan sát & Kiểm toán

* **Ghi log:** Dùng `structlog` với các trường bắt buộc `{tenant_id, request_id, agent, tool}`.
* **Sổ Nam Tào (Audit log):** Mỗi lần Agent dùng tool đều ghi lại `(tenant_id, agent, tool, input_hash, output_hash, latency_ms, cost_usd)` vào bảng Postgres không thể sửa đổi (immutable).

### §3.8 Tầng Máy Gặt - Harvester (Hoàn toàn độc lập với Suy luận AI)

Harvester là một **hệ thống thu thập dữ liệu tự hành**, bị tách rời hoàn toàn khỏi luồng Agent LLM. Nó tuân thủ nguyên tắc thép: **Thu thập Dữ liệu Không phải là Suy luận.** Máy gặt chỉ mang dữ liệu về, không bao giờ dùng LLM để suy nghĩ, và không chạy chung tiến trình với các Agent.

* **Động cơ:** Playwright + `playwright-stealth`, được kích hoạt theo lịch trình bởi **Celery Beat (cronjob)**.
* **Zero-hardcode:** Mọi nguồn cào được định nghĩa ở file **`scraper_config.yaml`** (URL, selector, nhịp độ, `tenant_id`). **Tuyệt đối không viết cứng URL vào code Python.**
* **Luồng 4 Bước:**
1. **Cào (Crawl)** — Tải trang web công khai về.
2. **Hồ Dữ liệu thô** — Lưu file thô, gắn nhãn `{tenant_id}` ngay lập tức.
3. **Lọc sạch (Clean)** — Cắt rác, xóa quảng cáo, lọc PII.
4. **Nạp Vector** — Băm nhỏ → `BAAI/bge-m3` → nhét vào **Qdrant** với bộ lọc `tenant_id` bắt buộc.


* **Tuân thủ:** Chỉ cào **dữ liệu công khai**. Không bao giờ cào dữ liệu mật của tenant khác. Phải gắn `tenant_id` ngay từ file thô đầu tiên, nếu thiếu sẽ tự động hủy bỏ.

---

## §4. KỶ LUẬT THỰC THI NGHIÊM NGẶT

1. **Bắt buộc dùng TDD.** Mọi thay đổi về Agent hay RAG đều phải Test trước. Logic RAG phải vượt qua **kiểm thử đa ngôn ngữ** (VN, EN, DE, CN).
2. **Commit siêu nhỏ.** Mỗi tính năng chạy được phải commit riêng lẻ theo chuẩn Conventional Commits.
3. **Không Ảo giác & Cách ly Tenant.** Bộ lọc `tenant_id` là bất khả xâm phạm trên mọi đường truyền tới Database.
4. **Không gọi API LLM trực tiếp.** Luôn thông qua ổ cắm `LLMClientBase`. Viết thẳng `openai.*` vào logic Agent sẽ bị đánh trượt ở khâu CI.
5. **Ranh giới Open-Core.** Lõi Core không chứa giao diện hay thanh toán. Bản Cloud không tự viết lại AI.

---

## §5. YÊU CẦU PHI CHỨC NĂNG

| Chỉ số | Mục tiêu |
| --- | --- |
| Độ trễ tìm kiếm RAG | p95 < 800ms (trên Mac M4) |
| Độ trễ gọi Tool LLM | p95 < 4s (Local) / < 2s (Cloud vLLM) |
| Rò rỉ dữ liệu chéo Tenant | Tỉ lệ = 0 tuyệt đối |
| Tỉ lệ Upload thành công | ≥ 95% trên mỗi nền tảng |
| Công suất nhúng (Embedding) | ≥ 500 bài/phút (Mac M4) |
| Chi phí tạo bài viết | ≤ $0.05 (Local), ≤ $0.30 (Cloud) |