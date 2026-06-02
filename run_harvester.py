"""Manual test runner for the Harvester engine (Chặng 0).

Usage::

    python run_harvester.py

Order of operations:
  1. Cleanup — delete Raw Data Lake files older than RAW_DATA_LAKE_TTL_HOURS.
  2. Discover plugins under extractors/plugins/.
  3. Run every enabled source in scraper_config.yaml with fault isolation.
  4. Land tagged raw JSON (and optional media) under raw_data_lake/texts/<tenant>/.
  5. Print a per-source summary report.

No LLM, no agent — pure data acquisition.
"""

from __future__ import annotations

import asyncio
import json

from app.core.config import settings
from app.infrastructure.harvester.engine import HarvesterEngine


async def main() -> None:
    engine = HarvesterEngine()

    # ── Step 1: TTL cleanup ──────────────────────────────────────────────
    print(f"→ Cleaning up data lake (TTL={settings.RAW_DATA_LAKE_TTL_HOURS}h) ...")
    cleanup = engine.cleanup()
    if cleanup["deleted_files"] or cleanup["deleted_dirs"]:
        print(
            f"   🗑  deleted {cleanup['deleted_files']} file(s), "
            f"{cleanup['deleted_dirs']} empty dir(s)  "
            f"[{cleanup['skipped']} kept]"
        )
    else:
        print(f"   ✓  nothing expired  [{cleanup['skipped']} file(s) kept]")

    # ── Step 2: Plugin discovery ─────────────────────────────────────────
    print("\n→ Discovering plugins ...")
    registry = engine.discover_plugins()
    for plugin_type, cls in sorted(registry.items()):
        print(f"   • {plugin_type:<16} → {cls.__module__}.{cls.__name__}")

    # ── Step 3–4: Run sources ────────────────────────────────────────────
    print("\n→ Running sources ...\n")
    report = await engine.run()

    # ── Step 5: Summary ──────────────────────────────────────────────────
    print("\n──────────── HARVEST REPORT ────────────")
    for entry in report["sources"]:
        status = entry["status"]
        mark = {"ok": "✅", "failed": "💥", "discarded": "🚫", "skipped": "⏭ "}.get(status, "⚠️ ")
        line = f"{mark} {entry['source']:<38} {status:<14} items={entry['items']}"
        if entry.get("error"):
            line += f"  ({entry['error']})"
        print(line)
    print("─────────────────────────────────────────")
    print(
        f"sources={len(report['sources'])}  "
        f"total_items={report['total_items']}  "
        f"failures={report['total_failures']}"
    )
    print("\nFull report:")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
