# ⚖️ TECH STACK RULE — Nyxara (OPEN-SOURCE · SINGLE REPO)

> **Status:** Constitutional for this repo. A PR that violates any rule below is auto-rejected.
> **License of this repo:** MIT (public, open-source).
> **Companion docs:** [`../docs/product-requirements.md`](../docs/product-requirements.md) · [`../docs/ai-agent-design.md`](../docs/ai-agent-design.md).

---

## §0. THE GOLDEN RULE — A LOCAL-FIRST, OPEN-SOURCE LEARNING ENGINE

**Nyxara** is an **OPEN-SOURCE (MIT)**, modular **multilingual RAG + agentic
engine** built as a learning vehicle — fork it for your niche (aimed at
seller-affiliate content automation, human-in-the-loop), run it 100% local. It
MUST run standalone in Docker / on a self-hosted box with **zero** dependency on
any external SaaS layer.

It is **not** a commercial product: there is no billing, no user accounts, no
admin dashboard, no second repo. It **does not auto-publish** — drafts go to a
human; sending uses official APIs. Keep the stack lean and focused:

| Concern | Approved technology |
|---|---|
| Language | **Python 3.11** |
| Web framework | **FastAPI** + Uvicorn |
| ORM / local DB | **SQLAlchemy** (+ Alembic migrations), PostgreSQL — for local config, source registry, run history, review queue |
| Vector DB | **Qdrant** (`qdrant-client`) |
| RAG (Phase 3) | Hybrid (dense bge-m3 + sparse BM25) · RRF · **cross-encoder rerank (`bge-reranker-v2-m3`)** · CRAG · metadata filtering · semantic chunking — all hand-built, all per-query flags (§5) |
| Async jobs | **Celery** + **Redis** broker |
| Inference | `LLMClientBase` → Ollama / Apple MLX (dev) · vLLM / Cloud API (scale) |
| Fine-tuning | LoRA on `Qwen2.5-7B` · GGUF quantization merge · embedding/domain fine-tuning (Phase 4) |
| Agent framework | LangGraph (Supervisor–Worker, human-in-the-loop) |
| Eval | RAGAS + custom metrics + A/B toggling — **basic eval from Phase 3** |
| MLOps | LangFuse / Prometheus + Grafana · DVC / W&B / MLflow (Phase 6, light) |
| Visual / Video — *OPTIONAL* | ComfyUI · SDXL / Flux · ControlNet · XTTS / CosyVoice · ffmpeg — **off the main path, needs GPU** |

Adding anything outside this list requires a note in the architecture spec.

---

## §1. OUT OF SCOPE BY DESIGN

This is a learning engine, not a SaaS. The following are **not built here** — not
because they belong in another repo, but because they are simply not the goal:

| # | Out of scope |
|---|---|
| 1.1 | Billing / invoicing / metered-charge / credit-wallet logic (`import stripe`, `TenantCredits`, etc.). Token counting emits **usage metadata for observability only** — there is nothing to debit. |
| 1.2 | User authentication, login/signup, password/passkey handling, OAuth flows, session issuance for end users. |
| 1.3 | A multi-user SaaS dashboard / RBAC admin panel / subscription-plan UI. |
| 1.4 | **Autonomous browser auto-posting** — stealth-browser publishing, scheduled auto-posting, encrypted stealth-session vaults. Teaches no AI skill, violates platform ToS, risks bans. Sending is **human-approved and goes through official APIs only.** *(Browser/Playwright use stays allowed **only** in the Harvester for scraping public pages — §4 — never for posting.)* |

A user-facing UI, if ever added, is a **thin optional** Streamlit/Gradio panel
that calls the same local API — it never becomes a tenancy/billing system.

> **`tenant_id` is a NAMESPACE, not a customer.** It lets one install host
> several niches/users side by side in Qdrant. The engine trusts and enforces it
> on every DB/Vector path; it does **not** manage identity, auth, or money.

---

## §2. WHAT THE ENGINE OWNS

- FastAPI orchestrator (`app/api`), domain/services logic (`app/services`),
  shared config & infra wiring (`app/core`).
- Harvester subsystem (`app/infrastructure/harvester/`) — see §4.
- RAG pipeline: chunking → embedding → Qdrant upsert/search (always with a
  `tenant_id` namespace payload filter); Hybrid + RRF + **cross-encoder rerank** +
  CRAG + metadata filtering + semantic chunking as it matures (Phase 3).
- LangGraph Supervisor–Worker agent graph (see `ai-agent-design.md`) with a
  **human review gate** before any send; optionally growing a Visual Director +
  Video Producer if the OPTIONAL Visual track is built.
- Celery workers for ingest / embedding / fine-tuning / video / long-running tasks.
- All LLM access goes through a single `LLMClientBase` abstraction — never call
  `openai.*` / `anthropic.*` / `transformers.pipeline(...)` directly.

---

## §3. ENFORCEMENT

| # | Rule |
|---|---|
| 3.1 | A CI job greps for forbidden patterns (`import stripe`, end-user auth/login flows, raw `openai.*`/`transformers.pipeline` in agent code) and **fails the build** on a match. |
| 3.2 | Approved dependencies only. Adding anything outside §0 requires a note in the architecture spec. |
| 3.3 | The engine MUST start and pass `GET /health` fully standalone, with no external SaaS secrets present. |
| 3.4 | When `INFERENCE_MODE=self_hosted`, no outbound HTTPS to OpenAI/Anthropic/Gemini (privacy-by-default for a local fork). CI greps to verify. This also **hard-disables the optional CRAG `web_search` correction tool** — in self-hosted mode CRAG self-corrects in-store only (re-query / widen-`top_k` / BM25 fallback). |
| 3.5 | **No autonomous publishing.** A reply is sent only after a human approval (`approved_by`) and only via a platform's **official API**. Browser-automation / stealth posting in agent or sender code is an instant reject; CI greps for it. (Harvester scraping of public pages is the only sanctioned browser use — §4.) |

---

## §4. Harvester (Phase 0 — Data Ingestion, binding)

| # | Rule |
|---|---|
| 4.1 | **Data Ingestion ≠ Inference.** The Harvester MUST NOT call an LLM, import agent code, or share a process with the agent graph. It only acquires and lands data. |
| 4.2 | **Zero-hardcode sources.** Every scraping target lives in `scraper_config.yaml` (URL, selectors, cadence, locale, `tenant_id`). A hardcoded URL literal in Python is an instant reject. |
| 4.3 | **Public data only.** Never scrape login-walled or private content. Respect `robots.txt` / platform ToS; rate-limit per source. |
| 4.4 | **`tenant_id` at the source.** Every harvested raw artifact is stamped with its `tenant_id` namespace at the Harvester layer (first landing). An artifact missing `tenant_id` is discarded, never ingested. |
| 4.5 | Pipeline order is fixed: **Crawl → Raw Data Lake → Filter (Clean) → Qdrant upsert** (with `tenant_id` namespace filter). No skipping the clean stage. |

---

## §5. RAG Implementation Philosophy (Phase 3+, binding)

> **Why this exists:** this is a learning engine. The point is to *own and
> understand* the retrieval math/flow — matching the by-hand BM25 + RRF already
> shipped — not to glue together opaque wrappers.

| # | Rule |
|---|---|
| 5.1 | **Retrieval logic is hand-built in pure Python** over `LLMClientBase` + `qdrant-client`: query transformation (Multi-Query, HyDE), hybrid fusion (RRF), parent-child (small-to-big) chunking, and context compression. |
| 5.2 | **No LangChain retriever wrappers** (`MultiQueryRetriever`, `ParentDocumentRetriever`, `ContextualCompressionRetriever`, etc.). They couple to LangChain's document-store abstraction and fight the hand-built Qdrant layer. |
| 5.3 | **LangGraph owns flow only** — the CRAG state machine, routing, and self-correction loops. It does **not** own retrieval primitives. |
| 5.4 | **Every advanced technique is a flag** (`query_transform`, `chunk_strategy`, `compress`), defaulting off, so a fork scales pipeline cost (and latency) to its niche's complexity. |
| 5.5 | **Context compression uses an `LLMClientBase` extractor, not LLMLingua** — keep the stack lean and local. LLMLingua, if ever added, is a Phase 6 note per §0. The extractor copies sentences **verbatim** (no paraphrasing) and falls back to the raw chunk if an extracted sentence is not a substring of the source. |
