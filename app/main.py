"""FastAPI entrypoint for n-assistant-core (open-source).

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI

app = FastAPI(
    title="N Assistant — Core API (Open-Source)",
    description="MIT-licensed AI & backend core: RAG pipeline, agent orchestration.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe. No auth, no tenant context required."""
    return {"status": "ok", "service": "core-api-opensource"}
