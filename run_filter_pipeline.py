"""Run the 3-layer filter pipeline over all items in the Raw Data Lake.

Usage:
    docker compose run --rm --no-deps core-api python run_filter_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import structlog

from app.application.services.content_filter_pipeline import run_filter_pipeline

logger = structlog.get_logger()

RAW_DATA_LAKE = Path("raw_data_lake/texts")
OUTPUT_PATH   = Path("raw_data_lake/filtered/approved.json")


def load_raw_items() -> list[dict]:
    """Read all RawEnvelope JSON files and extract the inner item dicts."""
    items = []
    for f in RAW_DATA_LAKE.rglob("*.json"):
        try:
            envelope = json.loads(f.read_text(encoding="utf-8"))
            item = envelope.get("item", {})
            # Carry tenant + source metadata forward for traceability.
            item["tenant_id"]   = envelope.get("tenant_id")
            item["source_name"] = envelope.get("source_name")
            item["harvest_id"]  = envelope.get("harvest_id")
            items.append(item)
        except Exception as exc:
            logger.warning("load_failed", file=str(f), error=str(exc))
    return items


async def main() -> None:
    raw_items = load_raw_items()
    logger.info("raw_items_loaded", count=len(raw_items))

    approved = await run_filter_pipeline(raw_items, output_path=OUTPUT_PATH)

    print(f"\n{'─'*60}")
    print(f"  {len(approved)} / {len(raw_items)} items approved")
    print(f"  Saved → {OUTPUT_PATH}")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
