# ⚖️ TECH STACK RULE — n-assistant-core (OPEN-SOURCE)

> **Status:** Constitutional for this repo. A PR that violates any rule below is auto-rejected.
> **License of this repo:** MIT (public, open-source).
> **Companion docs:** [`../docs/product-requirements.md`](../docs/product-requirements.md) · [`../docs/ai-agent-design.md`](../docs/ai-agent-design.md).

---

## §0. THE GOLDEN RULE — THIS IS THE OPEN-SOURCE REPO

`n-assistant-core` is the **OPEN-SOURCE (MIT)** AI & backend core. It MUST run
standalone in Docker / on a self-hosted box with **zero** dependency on any
commercial SaaS layer.

**BẮT BUỘC / MANDATORY:** Chỉ tập trung vào stack sau:

| Concern | Approved technology |
|---|---|
| Language | **Python 3.11** |
| Web framework | **FastAPI** + Uvicorn |
| ORM / DB | **SQLAlchemy** (+ Alembic migrations), PostgreSQL |
| Vector DB | **Qdrant** (`qdrant-client`) |
| Async jobs | **Celery** + **Redis** broker |

---

## §1. ABSOLUTELY FORBIDDEN IN THIS REPO

> ❌ **TUYỆT ĐỐI KHÔNG** code logic Authentication người dùng hay Billing (Stripe) vào repo này.

| # | Forbidden | Where it belongs instead |
|---|---|---|
| 1.1 | `import stripe` / any billing, invoicing, metered-charge, `TenantCredits` wallet debit logic. | `n-assistant-cloud` (commercial) |
| 1.2 | User authentication, login/signup, password/passkey handling, OAuth provider flows, session issuance. | `n-assistant-cloud` |
| 1.3 | SaaS dashboard / React / Next.js / any web UI components. | `n-assistant-cloud` |
| 1.4 | RBAC admin panels, tenant-management admin screens, subscription plan UI. | `n-assistant-cloud` |

Core **receives** a verified `tenant_id` (from the cloud layer over the REST/WS
API), trusts and enforces it on every DB/Vector query, but does **NOT** manage
identity, auth, or money itself.

---

## §2. WHAT CORE *DOES* OWN

- FastAPI orchestrator (`app/api`), domain/services logic (`app/services`),
  shared config & infra wiring (`app/core`).
- RAG pipeline: chunking → embedding → Qdrant upsert/search (always with a
  `tenant_id` payload filter).
- LangGraph Supervisor–Worker agent graph (see `ai-agent-design.md`).
- Celery workers for ingest / embedding / long-running tasks.
- All LLM access goes through a single `LLMClientBase` abstraction — never call
  `openai.*` / `anthropic.*` / `transformers.pipeline(...)` directly.

---

## §3. ENFORCEMENT

| # | Rule |
|---|---|
| 3.1 | A CI job greps for forbidden imports (`stripe`, auth/billing modules, Next.js artifacts) and **fails the build** on a match. |
| 3.2 | Approved dependencies only. Adding anything outside the table in §0 requires an RFC. |
| 3.3 | Core MUST start and pass `GET /health` with **no** secrets from the commercial layer present. |
| 3.4 | Cross-repo calls go only through the documented REST/WebSocket API — never a shared private package. |
