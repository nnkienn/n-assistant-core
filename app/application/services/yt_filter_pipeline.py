"""YouTube Shorts content filter pipeline — 3-layer skills integration.

Mirrors the EXACT SAME architecture as the Twitter filter pipeline
(content_filter_pipeline.py), adapted for YouTube Shorts' data model:

Pipeline position in the system:
    [Harvester] yt-dlp → Raw transcript + metadata
                                                    ↓
                            [THIS MODULE] Filter (Clean) — 3 layers
                                                    ↓
                                    Raw Data Lake / Qdrant upsert

Execution order is non-negotiable (CRITICAL PERFORMANCE RULE):
    1. Layer 1 — YT Heuristic  (O(1), CPU, no I/O)        ← runs FIRST, always
    2. Layer 2 — YT Text Clean (O(n), CPU, no I/O)        ← only if L1 passes
    3. Layer 3 — LLM Judge     (async API call, ~300 ms)   ← only if L1+L2 pass

Never reorder: the LLM call costs money and time; the heuristic gate kills
obvious junk for free. A Short must earn each successive layer.

Key difference from Twitter pipeline:
  - Layer 3 sends "{Video Title}: {Cleaned Transcript}" to the LLM,
    not just the tweet text — because a Shorts transcript alone lacks context.

Usage (as a library)::

    from app.application.services.yt_filter_pipeline import run_yt_filter_pipeline

    approved = await run_yt_filter_pipeline(raw_items, output_path=Path("out.json"))

Usage (standalone demo / local testing)::

    python -m app.application.services.yt_filter_pipeline
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog
import yaml

from app.application.services.llm_evaluator import BATCH_SIZE, batch_is_high_quality
from app.infrastructure.harvester.filters.yt_heuristic_filter import is_viable_short
from app.infrastructure.harvester.filters.yt_text_cleaner import clean_transcript

logger = structlog.get_logger(__name__)

# Zero-hardcode: config path comes from here only for the standalone demo.
# Production callers should read scraper_config.yaml via settings.HARVESTER_CONFIG_PATH.
_DEFAULT_CONFIG_PATH = Path("scraper_config.yaml")


def _load_yt_heuristic_config(config_path: Path = _DEFAULT_CONFIG_PATH) -> dict:
    """Load the ``filter_config.youtube_shorts_heuristic`` section from scraper_config.yaml."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return raw.get("filter_config", {}).get("youtube_shorts_heuristic", {})


async def run_yt_filter_pipeline(
    raw_items: list[dict[str, Any]],
    *,
    output_path: Path | None = None,
    config_path: Path = _DEFAULT_CONFIG_PATH,
) -> list[dict[str, Any]]:
    """Run the 3-layer anti-spam filter over a batch of raw YouTube Shorts dicts.

    Typical input: items loaded from Raw Data Lake JSON envelopes written by
    the Harvester engine (``RawEnvelope.item`` dicts from the youtube_shorts
    plugin). Each item should have:
      - ``content``  — the raw transcript text (may be empty/None)
      - ``title``    — the video title (used in Layer 3 combined evaluation)
      - ``metadata`` — optional dict with platform provenance

    Args:
        raw_items:   List of raw YouTube Shorts dicts.
        output_path: If given, the approved items are written as pretty JSON.
                     Parent directories are created automatically.
        config_path: Path to scraper_config.yaml (for heuristic thresholds).

    Returns:
        The subset of items that passed all three layers, each augmented with
        a ``clean_content`` key holding the noise-stripped transcript.

    Pipeline stats are emitted as a single ``yt_pipeline_complete`` structured log.
    """
    heuristic_cfg = _load_yt_heuristic_config(config_path)
    approved: list[dict[str, Any]] = []

    stats: dict[str, int] = {
        "total":     len(raw_items),
        "pass_l1":   0,
        "pass_l2":   0,
        "pass_l3":   0,
        "llm_calls": 0,  # actual API calls = ceil(pass_l2 / BATCH_SIZE)
    }

    # ── Layers 1 + 2: CPU-only pre-filter ────────────────────────────────
    candidates: list[tuple[dict[str, Any], str]] = []
    for raw in raw_items:
        transcript: str = raw.get("content", "") or ""
        title: str = raw.get("title", "") or ""
        log = logger.bind(
            source_url=raw.get("source_url", "unknown"),
            title=title[:60],
        )

        # ── Layer 1: Heuristic gate (Early Exit) ─────────────────────────
        if not is_viable_short(transcript, heuristic_cfg, title=title):
            log.debug("yt_pipeline_reject_l1_heuristic")
            continue
        stats["pass_l1"] += 1

        # ── Layer 2: Text cleaner ────────────────────────────────────────
        # Clean the description. If description is empty but title passed
        # L1 (enough combined words), use title as the text signal.
        clean_text = clean_transcript(transcript) if transcript else ""
        if not clean_text:
            # Fallback: title alone carries the topical signal for Shorts.
            clean_text = title.strip()
        if not clean_text:
            log.debug("yt_pipeline_reject_l2_empty_after_clean")
            continue
        stats["pass_l2"] += 1

        candidates.append((raw, clean_text))

    logger.info("yt_pipeline_l1_l2_complete",
                total=stats["total"], candidates=len(candidates))

    # ── Layer 3: Batch LLM gate ───────────────────────────────────────────
    # Reuses the EXACT SAME batch_is_high_quality() from llm_evaluator.py.
    # Key adaptation: we send "{Title}: {Cleaned Transcript}" so the LLM has
    # full context to judge content quality.
    _BATCH_DELAY   = 3.0   # seconds between calls (rate-limit etiquette)
    _MAX_RETRIES   = 3     # retries on 429
    _RETRY_BACKOFF = 60.0  # wait 60s on per-day limit, 5s on per-min limit

    for batch_idx, batch_start in enumerate(range(0, len(candidates), BATCH_SIZE)):
        batch = candidates[batch_start: batch_start + BATCH_SIZE]

        # Compose the LLM input: "{Video Title}: {Cleaned Transcript}"
        texts = [
            f"{raw.get('title', '')}: {clean}" for raw, clean in batch
        ]

        if batch_idx > 0:
            await asyncio.sleep(_BATCH_DELAY)

        verdicts: list[bool] = []
        for attempt in range(_MAX_RETRIES):
            try:
                verdicts = await batch_is_high_quality(texts)
                stats["llm_calls"] += 1
                break
            except Exception as exc:  # noqa: BLE001
                err = str(exc)
                is_per_min = "per-min"  in err
                is_per_day = "per-day"  in err
                wait = 5.0 if is_per_min else _RETRY_BACKOFF
                if attempt < _MAX_RETRIES - 1 and (is_per_min or is_per_day):
                    logger.warning("yt_pipeline_l3_rate_limit_retry",
                                   attempt=attempt + 1, wait=wait)
                    await asyncio.sleep(wait)
                else:
                    logger.error("yt_pipeline_l3_batch_error",
                                 error=err[:120], error_type=type(exc).__name__)
                    break

        for (raw, clean_text), passed in zip(batch, verdicts):
            if passed:
                stats["pass_l3"] += 1
                approved.append({**raw, "clean_content": clean_text})
                logger.info("yt_pipeline_approved",
                            source_url=raw.get("source_url"),
                            title=raw.get("title", "")[:60])
            else:
                logger.debug("yt_pipeline_reject_l3",
                             source_url=raw.get("source_url"))

    logger.info("yt_pipeline_complete", **stats)

    # ── Persist approved items to JSON ───────────────────────────────────
    if output_path and approved:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(approved, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("yt_approved_saved", path=str(output_path), count=len(approved))

    return approved


# ── Standalone mock demo ──────────────────────────────────────────────────────
async def _demo() -> None:
    """Demonstrate the full YouTube pipeline with representative mock items.

    Run with:
        python -m app.application.services.yt_filter_pipeline

    Expected flow:
        Short 1 → PASS  (genuine AI tool walkthrough with solid transcript)
        Short 2 → FAIL  L1 (None transcript — music-only Short)
        Short 3 → FAIL  L1 (transcript too short — 4 words)
        Short 4 → FAIL  L2 (transcript is all [Music] tags → empty after clean)
        Short 5 → PASS  (detailed LLM news content)
    """
    import logging
    import structlog as sl

    sl.configure(
        processors=[
            sl.processors.add_log_level,
            sl.processors.TimeStamper(fmt="%H:%M:%S"),
            sl.dev.ConsoleRenderer(),
        ],
        wrapper_class=sl.make_filtering_bound_logger(logging.DEBUG),
        logger_factory=sl.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    mock_shorts: list[dict[str, Any]] = [
        {
            "source_url": "https://www.youtube.com/shorts/abc123",
            "title": "5 AI Tools That Changed My Workflow in 2025",
            "content": (
                "I've been testing AI tools all year and these five completely "
                "changed how I work. Number one is Cursor, the AI code editor. "
                "It now ships with background agents that can refactor entire "
                "modules while you review pull requests. Number two is NotebookLM "
                "which turns any PDF into a podcast. I used it to summarize a "
                "300-page research paper in under ten minutes."
            ),
            "metadata": {"platform": "YouTube", "channel": "TechReviewer"},
        },
        {
            # Fails L1: no title + no content = zero text signal
            "source_url": "https://www.youtube.com/shorts/def456",
            "title": "",
            "content": None,
            "metadata": {"platform": "YouTube", "channel": "LoFiChannel"},
        },
        {
            # Fails L1: combined title + content too short (6 words < 10)
            "source_url": "https://www.youtube.com/shorts/ghi789",
            "title": "Quick Tip",
            "content": "Hey check this out",
            "metadata": {"platform": "YouTube", "channel": "RandomUser"},
        },
        {
            # Fails L2: transcript is ALL noise tags → empty after cleaning
            "source_url": "https://www.youtube.com/shorts/jkl012",
            "title": "Dance Challenge 2025",
            "content": "[Music] [Applause] [Music] [Laughter] [Music] [Cheering]",
            "metadata": {"platform": "YouTube", "channel": "DanceStar"},
        },
        {
            "source_url": "https://www.youtube.com/shorts/mno345",
            "title": "GPT-5 Just Leaked — Here's What We Know",
            "content": (
                "OpenAI accidentally published a research paper that reveals "
                "GPT-5's architecture details. The model uses a mixture of "
                "experts with 16 active experts out of 128 total. Training "
                "data includes synthetic reasoning chains generated by O3. "
                "The context window is reportedly two million tokens with "
                "near-perfect recall. Benchmark scores show it matches "
                "PhD-level performance on GPQA Diamond. This is a massive "
                "leap from GPT-4o and puts serious pressure on Anthropic "
                "and Google to respond."
            ),
            "metadata": {"platform": "YouTube", "channel": "AINewsDaily"},
        },
    ]

    output = Path("raw_data_lake/filtered/yt_demo_approved.json")
    results = await run_yt_filter_pipeline(mock_shorts, output_path=output)

    print(f"\n{'─'*60}")
    print(f"  Pipeline result: {len(results)} / {len(mock_shorts)} Shorts approved")
    print(f"{'─'*60}")
    for item in results:
        print(f"  ✓  {item['source_url']}")
        print(f"     {item.get('title', '')[:60]}")
        print(f"     {item['clean_content'][:90]}…")
    if results:
        print(f"\n  Saved → {output}")
    print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(_demo())
