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
