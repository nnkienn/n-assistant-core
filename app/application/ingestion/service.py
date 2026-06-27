"""IngestionService — turn cleaned JSON into searchable vectors.

It depends ONLY on the ports (``Embedder``, ``VectorStore``), never on the
concrete bge-m3 / Qdrant classes. So it's testable with fakes and the backends
are swappable. The wiring (which adapter) happens at the edge (``cli.py``), not
here — that's dependency injection.

Flow:  load JSON → chunk each item → embed all chunks → ensure collection →
upsert (every payload stamped with tenant_id).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from app.application.ingestion.chunker import chunk_text
from app.domain.ports.embedder import Embedder
from app.domain.ports.vector_store import VectorStore

logger = structlog.get_logger(__name__)


class IngestionService:
    def __init__(self, embedder: Embedder, store: VectorStore) -> None:
        # Injected ports — the service never builds its own model/DB client.
        self._embedder = embedder
        self._store = store

    async def ingest_file(self, path: str | Path, *, collection: str, tenant_id: str) -> int:
        """Ingest one approved-JSON file. Returns the number of chunks stored."""
        items = json.loads(Path(path).read_text(encoding="utf-8"))

        texts: list[str] = []
        payloads: list[dict[str, Any]] = []
        for item in items:
            content = item.get("clean_content") or item.get("content") or ""
            for chunk in chunk_text(content):  # 1 item → 1+ chunks (mạnh #3 strategy)
                texts.append(chunk)
                payloads.append(
                    {
                        # tenant_id namespace on EVERY chunk — fall back to the
                        # run's tenant_id if the item didn't carry one.
                        "tenant_id": item.get("tenant_id") or tenant_id,
                        "source_url": item.get("source_url", ""),
                        "locale": item.get("locale", ""),
                        "text": chunk,
                    }
                )

        if not texts:
            logger.warning("ingest_empty", path=str(path))
            return 0

        vectors = await self._embedder.embed(texts)           # compute-bound, sync
        self._store.ensure_collection(collection, dim=len(vectors[0]))
        count = self._store.upsert(collection, vectors, payloads)
        logger.info("ingested", path=str(path), items=len(items), chunks=count)
        return count
