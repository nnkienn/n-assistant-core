"""FastAPI entrypoint for n-assistant-core (open-source).

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI

from app.core.config import settings

# ── Structlog configuration ────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        (
            structlog.dev.ConsoleRenderer()
            if settings.DEBUG
            else structlog.processors.JSONRenderer()
        ),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.LOG_LEVEL),
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# ── FastAPI application ────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="MIT-licensed AI & backend core: RAG pipeline, agent orchestration.",
    version=settings.APP_VERSION,
)


@app.on_event("startup")
async def _on_startup() -> None:
    logger.info(
        "startup",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        inference_provider=settings.INFERENCE_PROVIDER,
        inference_model=settings.INFERENCE_MODEL,
        debug=settings.DEBUG,
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe. No auth, no tenant context required."""
    return {"status": "ok", "service": "core-api-opensource"}
