"""Manual test runner for the Harvester engine (Chặng 0).

Usage::

    python run_harvester.py

Discovers plugins, runs every enabled source in ``scraper_config.yaml`` with
fault isolation, lands tagged raw JSON under ``raw_data_lake/texts/<tenant>/``,
and prints a per-source summary. No LLM, no agent — pure data acquisition.
"""

from __future__ import annotations

import asyncio
import json

from app.infrastructure.harvester.engine import HarvesterEngine


async def main() -> None:
    engine = HarvesterEngine()

    print("→ Discovering plugins ...")
    registry = engine.discover_plugins()
    for plugin_type, cls in sorted(registry.items()):
        print(f"   • {plugin_type:<14} → {cls.__module__}.{cls.__name__}")

    print("\n→ Running sources ...\n")
    report = await engine.run()

    print("\n──────────── HARVEST REPORT ────────────")
    for entry in report["sources"]:
        status = entry["status"]
        mark = {"ok": "✅", "failed": "💥", "discarded": "🚫"}.get(status, "⚠️ ")
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
