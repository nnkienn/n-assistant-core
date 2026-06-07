"""Run the 3-layer YouTube Shorts filter pipeline over all YT items in the Raw Data Lake.

Mirrors run_filter_pipeline.py but targets youtube_shorts plugin output only.

Usage:
    docker compose run --rm --no-deps core-api python run_yt_filter_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import structlog

from app.application.services.yt_filter_pipeline import run_yt_filter_pipeline

logger = structlog.get_logger()

RAW_DATA_LAKE = Path("raw_data_lake/texts")
OUTPUT_PATH   = Path("raw_data_lake/filtered/yt_approved.json")


def load_yt_raw_items() -> list[dict]:
    """Read RawEnvelope JSON files from youtube_shorts plugin directories."""
    items = []
    for tenant_dir in RAW_DATA_LAKE.iterdir():
        if not tenant_dir.is_dir():
            continue
        yt_dir = tenant_dir / "youtube_shorts"
        if not yt_dir.exists():
            continue
        for f in yt_dir.rglob("*.json"):
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
    raw_items = load_yt_raw_items()
    logger.info("yt_raw_items_loaded", count=len(raw_items))

    approved = await run_yt_filter_pipeline(raw_items, output_path=OUTPUT_PATH)

    print(f"\n{'─'*60}")
    print(f"  {len(approved)} / {len(raw_items)} YouTube Shorts approved")
    print(f"  Saved → {OUTPUT_PATH}")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
