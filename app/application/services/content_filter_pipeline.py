"""Anti-spam content filter pipeline — Chặng 0.5 (core/pipeline).

Pipeline position in the system (tech-stack-rule.md §4.5):
    [Harvester] Crawl → Raw Data Lake
                                      ↓
                          [THIS MODULE] Filter (Clean)
                                      ↓
                              Qdrant upsert (next stage)

Execution order is non-negotiable (CRITICAL PERFORMANCE RULE):
    1. Layer 1 — Heuristic  (O(1), CPU, no I/O)        ← runs FIRST, always
    2. Layer 2 — Text Clean (O(n), CPU, no I/O)        ← only if L1 passes
    3. Layer 3 — LLM Judge  (async API call, ~300 ms)  ← only if L1+L2 pass

Never reorder: the LLM call costs money and time; the heuristic gate kills
obvious junk for free. A tweet must earn each successive layer.

Usage (as a library)::

    from app.application.services.content_filter_pipeline import run_filter_pipeline

    approved = await run_filter_pipeline(raw_items, output_path=Path("out.json"))

Usage (standalone demo / local testing)::

    python -m app.application.services.content_filter_pipeline
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog
import yaml

from app.application.services.llm_evaluator import BATCH_SIZE, batch_is_high_quality
from app.infrastructure.harvester.filters.heuristic_filter import is_clean_tweet
from app.infrastructure.harvester.filters.text_cleaner import clean_noise

logger = structlog.get_logger(__name__)

# Zero-hardcode: config path comes from here only for the standalone demo.
# Production callers should read scraper_config.yaml via settings.HARVESTER_CONFIG_PATH.
_DEFAULT_CONFIG_PATH = Path("scraper_config.yaml")


def _load_heuristic_config(config_path: Path = _DEFAULT_CONFIG_PATH) -> dict:
    """Load the ``filter_config.heuristic`` section from scraper_config.yaml."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return raw.get("filter_config", {}).get("heuristic", {})


async def run_filter_pipeline(
    raw_items: list[dict[str, Any]],
    *,
    output_path: Path | None = None,
    config_path: Path = _DEFAULT_CONFIG_PATH,
) -> list[dict[str, Any]]:
    """Run the 3-layer anti-spam filter over a batch of raw tweet dicts.

    Typical input: items loaded from Raw Data Lake JSON envelopes written by
    the Harvester engine (``RawEnvelope.item`` dicts with at minimum a
    ``content`` key containing the tweet text).

    Args:
        raw_items:   List of raw tweet dicts. Each must have a ``content`` key.
        output_path: If given, the approved items are written as pretty JSON.
                     Parent directories are created automatically.
        config_path: Path to scraper_config.yaml (for heuristic thresholds).

    Returns:
        The subset of items that passed all three layers, each augmented with
        a ``clean_content`` key holding the noise-stripped text.

    Pipeline stats are emitted as a single ``pipeline_complete`` structured log.
    """
    heuristic_cfg = _load_heuristic_config(config_path)
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
        text: str = raw.get("content", "")
        log = logger.bind(source_url=raw.get("source_url", "unknown"))

        if not is_clean_tweet(text, heuristic_cfg):
            log.debug("pipeline_reject_l1_heuristic")
            continue
        stats["pass_l1"] += 1

        clean_text = clean_noise(text)
        if not clean_text:
            log.debug("pipeline_reject_l2_empty_after_clean")
            continue
        stats["pass_l2"] += 1

        candidates.append((raw, clean_text))

    logger.info("pipeline_l1_l2_complete",
                total=stats["total"], candidates=len(candidates))

    # ── Layer 3: Batch LLM gate ───────────────────────────────────────────
    # BATCH_SIZE tweets per API call — 10× more quota-efficient.
    # 3s delay between calls stays under 20 req/min free-tier limit.
    _BATCH_DELAY   = 3.0   # seconds between calls
    _MAX_RETRIES   = 3     # retries on 429
    _RETRY_BACKOFF = 60.0  # wait 60s on per-day limit, 5s on per-min limit

    for batch_idx, batch_start in enumerate(range(0, len(candidates), BATCH_SIZE)):
        batch = candidates[batch_start: batch_start + BATCH_SIZE]
        texts = [clean for _, clean in batch]

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
                is_per_min  = "per-min"  in err
                is_per_day  = "per-day"  in err
                wait = 5.0 if is_per_min else _RETRY_BACKOFF
                if attempt < _MAX_RETRIES - 1 and (is_per_min or is_per_day):
                    logger.warning("pipeline_l3_rate_limit_retry",
                                   attempt=attempt + 1, wait=wait)
                    await asyncio.sleep(wait)
                else:
                    logger.error("pipeline_l3_batch_error",
                                 error=err[:120], error_type=type(exc).__name__)
                    break

        for (raw, clean_text), passed in zip(batch, verdicts):
            if passed:
                stats["pass_l3"] += 1
                approved.append({**raw, "clean_content": clean_text})
                logger.info("pipeline_approved", source_url=raw.get("source_url"))
            else:
                logger.debug("pipeline_reject_l3", source_url=raw.get("source_url"))

    logger.info("pipeline_complete", **stats)

    # ── Persist approved items to JSON ───────────────────────────────────
    if output_path and approved:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(approved, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("approved_saved", path=str(output_path), count=len(approved))

    return approved


# ── Standalone mock demo ──────────────────────────────────────────────────────
async def _demo() -> None:
    """Demonstrate the full pipeline with five representative mock tweets.

    Run with:
        python -m app.application.services.content_filter_pipeline

    Expected flow:
        Tweet 1  → PASS  (informative AI update, meets all thresholds)
        Tweet 2  → FAIL  L1 (hashtag spam + crypto terms)
        Tweet 3  → FAIL  L1 (too short — 1 word)
        Tweet 4  → FAIL  L1 (starts with @)
        Tweet 5  → PASS  (detailed Cursor + agent content)
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

    mock_tweets: list[dict[str, Any]] = [
        {
            "source_url": "https://x.com/user/status/1",
            "content": (
                "Claude 3.5 Sonnet just dropped and the context window is enormous. "
                "We benchmarked it on our internal LLM eval suite — it beats GPT-4o "
                "on 8 out of 10 tasks, especially on multi-step reasoning and code. "
                "Here's a full breakdown with numbers and methodology."
            ),
        },
        {
            # Fails L1: starts with hashtag spam, crypto/nft terms (>3 hashtags)
            "source_url": "https://x.com/spammer/status/2",
            "content": (
                "FREE CRYPTO!! Join our AI airdrop #nft #web3 #defi #crypto "
                "#blockchain #giveaway 🚀🚀🚀🚀🚀🚀"
            ),
        },
        {
            # Fails L1: too short (1 word, below min_words=15)
            "source_url": "https://x.com/user/status/3",
            "content": "lol",
        },
        {
            # Fails L1: starts with @-mention (casual reply, not broadcast content)
            "source_url": "https://x.com/user/status/4",
            "content": (
                "@gdb @sama @karpathy agreed on the scaling hypothesis, "
                "next token prediction is still underrated imho"
            ),
        },
        {
            "source_url": "https://x.com/user/status/5",
            "content": (
                "Cursor just shipped multi-file edit with background AI agents. "
                "Tested it on a 50k-line TypeScript monorepo — it refactored the "
                "entire auth module in under 3 minutes, no hallucinations, all tests "
                "green. This fundamentally changes how engineering teams do code review."
            ),
        },
    ]

    output = Path("raw_data_lake/filtered/demo_approved.json")
    results = await run_filter_pipeline(mock_tweets, output_path=output)

    print(f"\n{'─'*60}")
    print(f"  Pipeline result: {len(results)} / {len(mock_tweets)} tweets approved")
    print(f"{'─'*60}")
    for item in results:
        print(f"  ✓  {item['source_url']}")
        print(f"     {item['clean_content'][:90]}…")
    if results:
        print(f"\n  Saved → {output}")
    print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(_demo())
