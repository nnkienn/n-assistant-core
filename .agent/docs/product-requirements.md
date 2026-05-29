<!--
═══════════════════════════════════════════════════════════════════════════
🟢 REPO SCOPE BANNER — n-assistant-core (MIT · OPEN-SOURCE)
═══════════════════════════════════════════════════════════════════════════
This is the COPY of the master spec living inside the OPEN-SOURCE core repo.
It is provided so every agent/contributor understands the FULL system, but the
boundary below is BINDING for anything implemented in THIS repo:

  • THIS repo (core) implements ONLY: FastAPI orchestrator, RAG pipeline,
    LangGraph agent workflows, Qdrant integration, Celery jobs, LLM clients.
  • The following sections are CONTEXT ONLY — they belong to n-assistant-cloud
    (commercial, closed-source) and MUST NOT be implemented here:
        §3.1 Next.js / i18n UI layer
        §3.6 Billing · Stripe · TenantCredits wallet
        Authentication / user management / SaaS dashboard / RBAC admin UI
  • Cross-repo communication is ONLY via the documented REST/WebSocket API.

See [`../rules/tech-stack-rule.md`](../rules/tech-stack-rule.md) for the
enforceable open-source boundary rules.
═══════════════════════════════════════════════════════════════════════════
-->

# 🌍 MASTER GLOBAL ARCHITECTURE SPECIFICATION — N ASSISTANT V2.0

> **DOCUMENT CLASSIFICATION:** Core engineering spec. Binding for every AI agent and human contributor on the project.
> **PROJECT VISION:** N Assistant is a Multi-tenant B2B SaaS AI Marketing Agent on the "Open-Core" model. Three architectural guarantees: (1) tenant data isolation via `tenant_id`-scoped RAG, (2) Hybrid Dual-Engine inference (Local + Cloud), (3) Omnichannel auto-upload via Playwright.
> **LANGUAGES SUPPORTED END-TO-END:** Vietnamese (VN), English (EN), German (DE), Chinese (CN).
> **CONSTITUTIONAL FILES:** This doc · [`../rules/tech-stack-rule.md`](../rules/tech-stack-rule.md) · [`../orchestration/ai-agent-design.md`](../orchestration/ai-agent-design.md).

---

## §0. GLOBAL STRATEGIC VISION (System Prompts)

Inject the locale-matched line into the root context of every working AI Agent.

- 🇻🇳 **Vietnamese:** N Assistant là nền tảng B2B SaaS AI Marketing tự hành đa người dùng (Multi-tenant). Cốt lõi: RAG bảo mật tuyệt đối theo `tenant_id`, suy luận Hybrid (Local/Cloud), và phân phối nội dung đa nền tảng.
- 🇬🇧 **English:** N Assistant is a Multi-tenant B2B SaaS AI Marketing Agent. The core is an isolated RAG system, hybrid inference routing (Local Open-Source vs Cloud API), and omnichannel auto-upload.
- 🇩🇪 **German:** N Assistant ist eine mandantenfähige B2B-SaaS-Plattform für KI-Marketing. Kernfunktionen: datenschutzkonformes RAG (DSGVO), hybride KI-Inferenz und automatisierte Omnichannel-Verteilung.
- 🇨🇳 **Chinese:** N Assistant 是一款多租户 B2B SaaS AI 营销自动化平台，核心优势：严格隔离的 RAG 知识库、混合大模型推理架构、全渠道自动发布工作流。

---

## §1. CODEBASE STRATEGY — Two-Repo Open-Core

| Repo | License | Stack | What lives here |
|---|---|---|---|
| **`n-assistant-core`** | MIT (public) | Python 3.11 · FastAPI · LangGraph · Qdrant · Playwright · PyTorch | AI inference orchestrator, RAG pipeline, agent workflows, auto-upload bots. Runs in Docker, native on Mac M4, or self-hosted GPU. |
| **`n-assistant-cloud`** | Commercial (private) | TypeScript · Next.js 15 · Tailwind v4 · Stripe · PostgreSQL · Clerk/custom Auth | Multi-tenant SaaS dashboard, billing, RBAC, `TenantCredits` wallet, audit log viewer. Calls `core` over REST/WebSocket. |

**Boundary contract (enforced by CI):**
- `core` MUST NOT import Stripe, tenant admin UI, billing logic.
- `cloud` MUST NOT re-implement an agent or call inference models directly.
- They communicate **only** through the documented REST/WebSocket API.

---

## §2. MULTI-LINGUAL DATA FLOW

```mermaid
graph TD
    Client[Next.js Client UI · i18n VN/EN/DE/CN] -->|JWT { user_id, tenant_id, role, locale }| API_Gateway[Cloud API / Auth]
    API_Gateway -->|REST + WebSocket| FastAPI[FastAPI Orchestrator · Supervisor]
    FastAPI <--> Postgres[(PostgreSQL · Users · Billing · Config · Audit)]
    FastAPI -->|Async tasks| RedisQueue[(Redis Queue)]
    RedisQueue --> CeleryWorker[Celery Workers]

    CeleryWorker <-->|tenant_id filter| EmbeddingModel[BAAI/bge-m3 Multilingual Embedding]
    EmbeddingModel <--> VectorDB[(Qdrant · isolated by tenant_id)]

    CeleryWorker <-->|LLMClientBase| LLMRouter{Dual-Engine LLM Router}
    LLMRouter -->|Tier-1 Production| CloudLLM[vLLM on Cloud GPU · or OpenAI fallback]
    LLMRouter -->|Tier-2 Dev / Self-host| LocalLLM[Ollama / Apple MLX · Llama-3.1-8B / Qwen2.5]

    CeleryWorker -->|Auto-upload trigger| PlaywrightBot[Playwright Headless Browser]
    PlaywrightBot --> TikTok[TikTok / Douyin]
    PlaywrightBot --> YouTube[YouTube Shorts]
    PlaywrightBot --> Facebook[FB / IG Reels]
```

---

## §3. DETAILED ARCHITECTURE LAYERS

### §3.1 Application & i18n Layer

- **Framework:** Next.js 15 (App Router).
- **UI/UX:** Tailwind v4 + Shadcn UI (style `radix-nova`).
- **i18n:** `next-intl` with `vi.json` / `en.json` / `de.json` / `zh.json`. Server components use `getTranslations`; client components use `useTranslations`.
- **State:** React Query (server cache) + Zustand (client UI state).
- **Auth:** Passkey + OAuth. JWT payload **MUST** contain `{ user_id, tenant_id, role, locale }`. Missing any field → middleware rejects.

### §3.2 Orchestration Layer

- **Framework:** Python FastAPI, Hexagonal Architecture (`app/domain`, `app/application`, `app/infrastructure`, `app/api`).
- **Responsibility:** receive request from UI, split documents (text splitter), drive the Supervisor-Worker agent graph (see [`ai-agent-design.md`](../orchestration/ai-agent-design.md)).
- **Security middleware:** `tenant_id` validator (rejects if missing or mismatched with route resource), JWT verifier, rate-limit by tenant.
- **Hard rule:** when `INFERENCE_MODE=self_hosted`, the orchestrator **MUST NOT** make any outbound HTTPS call to OpenAI/Anthropic/Gemini. CI gate verifies via `grep`.

### §3.3 Multi-Tenant RAG Layer

- **Vector DB:** Qdrant (Milvus acceptable alternative for high-write tenants).
- **Tenant isolation (Moat):** dedicated collection per tenant, or a single collection with **mandatory** `tenant_id` payload filter on every `upsert` and `search`. Cross-tenant query is an architectural violation.
- **Pipeline:** LangChain text splitters → `BAAI/bge-m3` embedding → Qdrant upsert with metadata `{tenant_id, doc_id, source, locale, ingested_at}`.
- **Cross-lingual capability:** `bge-m3` produces a single shared embedding space across VN/EN/DE/CN → a Vietnamese tenant can query their German knowledge base without translation pre-pass.

### §3.4 Dual-Engine AI Inference

A single OpenAI-compatible interface `LLMClientBase` lets agents swap engines via config without code change.

```python
class LLMClientBase(Protocol):
    async def complete(self, *, messages: list[Message], tools: list[Tool] | None = None, max_tokens: int) -> Completion: ...
```

| Tier | Use case | Implementation |
|---|---|---|
| **Local / Dev** | Zero-cost R&D, offline work, paranoid customers | Ollama (`:11434`) or Apple MLX on Mac M4 serving `Llama-3.1-8B-Instruct` or `Qwen2.5-7B` |
| **Production / Scale** | SaaS workload | vLLM on rented Cloud GPU (RunPod, AWS, Lambda Labs), or fallback to OpenAI / Claude 3.5 for peak demand |

Routing decision is config (`INFERENCE_MODE=local|cloud|hybrid`), not code. Agent code is identical across tiers.

### §3.5 Omnichannel Distribution Layer

- **Core:** Playwright (headless browser) mimicking human behavior to bypass platform API rate limits.
- **Session vault:** Cookies/sessions for TikTok, Facebook, YouTube → encrypted with **AES-256** (Python `cryptography` lib) → stored in PostgreSQL `tenant_sessions`. **Never plain-text.**
- **Bot-detection bypass:** `playwright-stealth`, residential proxy rotation per tenant.
- **Scheduling:** peak-time heuristic per tenant timezone; queue drain ≤1 video per platform per hour to avoid spike-detection.

### §3.6 Async Jobs & Monetization Layer

- **Workers:** Redis broker + Celery for any task >2s (PDF ingest, embedding batches, video render, Playwright upload). Frontend tracks progress via WebSocket or polling.
- **Billing:** Stripe Webhooks (**`n-assistant-cloud` only**). Subscription plans + metered usage.
- **Token Tracker:** count input/output tokens per call, debit `TenantCredits` wallet in real-time. Hard-stop the agent if credits exhausted.

### §3.7 Observability & Audit Layer

- **Logging:** `structlog` with mandatory fields `{tenant_id, request_id, agent, tool}`.
- **Tracing:** OpenTelemetry → Tempo/Jaeger.
- **Audit log:** every tool call writes `(tenant_id, agent, tool, input_hash, output_hash, model_version, latency_ms, cost_usd)` to an immutable Postgres table partitioned by `tenant_id`.
- **PII boundary:** tenant content is logged as content-hashes, not raw text.

---

## §4. STRICT EXECUTION DISCIPLINE

1. **TDD is mandatory.** Every RAG, agent, and tool change requires red→green→refactor. RAG logic requires **cross-language tests** (VN, EN, DE, CN). No green CI → no merge.
2. **Micro-commits.** Each working function ships as its own commit. Conventional Commits format.
3. **Zero-hallucination & Tenant-Isolation.** No library outside the approved stack without an RFC. `tenant_id` check is non-negotiable on every DB / Vector DB path.
4. **No raw LLM API calls.** Always go through `LLMClientBase`. Direct `openai.*` or `transformers.pipeline(...)` calls in agent code are a CI failure.
5. **Open-Core boundary.** `core` repo: no Stripe, no tenancy admin UI, no React dashboard. `cloud` repo: no agent re-implementations, no raw inference calls.

---

## §5. NON-FUNCTIONAL REQUIREMENTS

| Concern | Target |
|---|---|
| RAG query latency | p95 < 800ms on Mac M4 MPS for top-3 retrieval |
| LLM tool-call latency | p95 < 4s (local Llama-3.1-8B) / < 2s (Cloud vLLM) |
| Multi-tenant isolation | Cross-tenant data leak rate = 0 (verified by chaos test) |
| Auto-upload success rate | ≥ 95% per platform over 7-day window |
| Embedding throughput | ≥ 500 docs/min on Mac M4 MPS, ≥ 5000 docs/min on prod A10G |
| Cost per generated post | ≤ $0.05 on Tier-2 (local), ≤ $0.30 on Tier-1 (cloud) |
