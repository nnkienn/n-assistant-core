"""Unified 3-layer anti-spam filter pipeline.

Replaces the three separate pipeline files (content_filter_pipeline,
yt_filter_pipeline, yt_long_filter_pipeline) with a single parametrised
implementation. The strategy for each source type is declared once in
``_STRATEGIES`` — adding a new source type is one dict entry.

Pipeline position in the system:
    [Harvester] Crawl → Raw Data Lake
                                      ↓
                    [THIS MODULE] Filter (Clean) — 3 layers
                                      ↓
                           filtered/approved.json
                           (Qdrant-ready — Phase 2)

Execution order is non-negotiable (CRITICAL PERFORMANCE RULE):
    1. Layer 1 — Heuristic  (O(1) CPU, no I/O)         ← runs FIRST, always
    2. Layer 2 — Text Clean (O(n) CPU, no I/O)         ← only if L1 passes
    3. Layer 3 — LLM Judge  (async API call, ~300 ms)  ← only if L1+L2 pass

Usage::

    from app.application.ingestion.filter_pipeline import run_filter_pipeline

    approved = await run_filter_pipeline(
        raw_items, source_type="youtube_long", output_path=Path("out.json")
    )
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

import structlog
import yaml

from app.infrastructure.adapters.evaluator.llm_evaluator import BATCH_SIZE, batch_is_high_quality
from app.infrastructure.connectors.filters.x_heuristic import is_clean_tweet
from app.infrastructure.connectors.filters.x_text_cleaner import clean_noise
from app.infrastructure.connectors.filters.yt_long_heuristic import is_viable_long_segment
from app.infrastructure.connectors.filters.yt_shorts_heuristic import is_viable_short
from app.infrastructure.connectors.filters.yt_text_cleaner import clean_transcript

logger = structlog.get_logger(__name__)

SourceType = Literal["x_twscrape", "youtube_shorts", "youtube_long"]

_DEFAULT_CONFIG_PATH = Path("config/scraper_config.yaml")

# Parses "X-RateLimit-Reset": "<unix_ms>" from exception messages.
_RESET_TS_RE = re.compile(r"['\"]X-RateLimit-Reset['\"]:\s*['\"]?(\d+)['\"]?")


# ── Strategy declaration ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class _FilterStrategy:
    """Encapsulates the per-source-type variation points of the pipeline."""

    config_section: str                          # key under filter_config in YAML
    l1_fn: Callable[..., bool]                   # (text, cfg, **kw) -> bool
    l2_fn: Callable[[str], str]                  # (text) -> clean_str
    l1_pass_title: bool                          # pass title= kwarg to l1_fn
    l2_fallback_to_title: bool                   # use title if clean is empty (YT Shorts)
    initial_delay: float                         # seconds before first LLM batch
    batch_delay: float                           # seconds between successive batches
    format_llm: Callable[[str, str, dict], str]  # (title, clean, meta) -> LLM text


def _x_format(title: str, clean: str, meta: dict) -> str:
    return clean


def _shorts_format(title: str, clean: str, meta: dict) -> str:
    return f"{title}: {clean}" if title else clean


def _long_format(title: str, clean: str, meta: dict) -> str:
    start = meta.get("start_s", 0)
    end   = meta.get("end_s", 0)
    timing = f"[{start}s–{end}s]" if (start or end) else ""
    prefix = f"{title} {timing}".strip()
    return f"{prefix}: {clean}" if prefix else clean


_STRATEGIES: dict[str, _FilterStrategy] = {
    "x_twscrape": _FilterStrategy(
        config_section="heuristic",
        l1_fn=is_clean_tweet,
        l2_fn=clean_noise,
        l1_pass_title=False,
        l2_fallback_to_title=False,
        initial_delay=0.0,
        batch_delay=2.0,
        format_llm=_x_format,
    ),
    "youtube_shorts": _FilterStrategy(
        config_section="youtube_shorts_heuristic",
        l1_fn=is_viable_short,
        l2_fn=clean_transcript,
        l1_pass_title=True,
        l2_fallback_to_title=True,
        initial_delay=0.0,
        batch_delay=3.0,
        format_llm=_shorts_format,
    ),
    "youtube_long": _FilterStrategy(
        config_section="youtube_long_heuristic",
        l1_fn=is_viable_long_segment,
        l2_fn=clean_transcript,
        l1_pass_title=False,
        l2_fallback_to_title=False,
        initial_delay=1.0,
        batch_delay=3.0,
        format_llm=_long_format,
    ),
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_heuristic_config(source_type: str, config_path: Path) -> dict:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    section = _STRATEGIES[source_type].config_section
    return raw.get("filter_config", {}).get(section, {})


def _parse_rate_limit_reset(error_str: str, fallback: float = 60.0) -> float:
    """Extract wait time from X-RateLimit-Reset unix-ms header in error text."""
    match = _RESET_TS_RE.search(error_str)
    if match:
        reset_ms = int(match.group(1))
        wait = (reset_ms / 1000.0) - time.time() + 1.0
        return max(wait, 1.0)
    return fallback


# ── Public API ───────────────────────────────────────────────────────────────

async def run_filter_pipeline(
    raw_items: list[dict[str, Any]],
    source_type: SourceType,
    *,
    output_path: Path | None = None,
    config_path: Path = _DEFAULT_CONFIG_PATH,
) -> list[dict[str, Any]]:
    """Run the 3-layer anti-spam filter for the given source type.

    Args:
        raw_items:   Items from the Raw Data Lake for this source type.
        source_type: Which strategy to apply: "x_twscrape", "youtube_shorts",
                     or "youtube_long".
        output_path: Optional path to write approved items as JSON.
        config_path: Path to scraper_config.yaml (for heuristic thresholds).

    Returns:
        Items that passed all 3 layers, each augmented with a ``clean_content``
        key holding the noise-stripped text.

    Raises:
        ValueError: If ``source_type`` is not in the strategy registry.
    """
    if source_type not in _STRATEGIES:
        raise ValueError(
            f"Unknown source_type {source_type!r}. "
            f"Valid: {sorted(_STRATEGIES)}"
        )

    strategy = _STRATEGIES[source_type]
    cfg      = _load_heuristic_config(source_type, config_path)
    approved: list[dict[str, Any]] = []

    stats: dict[str, int] = {
        "total":     len(raw_items),
        "pass_l1":   0,
        "pass_l2":   0,
        "pass_l3":   0,
        "llm_calls": 0,
    }

    # ── Layers 1 + 2: CPU-only pre-filter ────────────────────────────────
    # Tuple: (raw_item, clean_text, title, metadata)
    candidates: list[tuple[dict[str, Any], str, str, dict]] = []

    for raw in raw_items:
        text  = raw.get("content", "") or ""
        title = raw.get("title", "")  or ""
        meta  = raw.get("metadata", {}) or {}
        log   = logger.bind(source_url=raw.get("source_url", "unknown"))

        l1_kwargs = {"title": title} if strategy.l1_pass_title else {}
        if not strategy.l1_fn(text, cfg, **l1_kwargs):
            log.debug(f"{source_type}_reject_l1")
            continue
        stats["pass_l1"] += 1

        clean = strategy.l2_fn(text)
        if not clean and strategy.l2_fallback_to_title:
            clean = title.strip()
        if not clean:
            log.debug(f"{source_type}_reject_l2_empty")
            continue
        stats["pass_l2"] += 1

        candidates.append((raw, clean, title, meta))

    logger.info(f"{source_type}_l1_l2_done",
                total=stats["total"], candidates=len(candidates))

    if not candidates:
        logger.info(f"{source_type}_pipeline_complete", **stats)
        return approved

    # ── Layer 3: Batch LLM gate ───────────────────────────────────────────
    _MAX_RETRIES = 4

    if strategy.initial_delay > 0:
        await asyncio.sleep(strategy.initial_delay)

    for batch_idx, batch_start in enumerate(range(0, len(candidates), BATCH_SIZE)):
        batch = candidates[batch_start: batch_start + BATCH_SIZE]
        texts = [strategy.format_llm(title, clean, meta)
                 for _, clean, title, meta in batch]

        if batch_idx > 0:
            await asyncio.sleep(strategy.batch_delay)

        verdicts: list[bool] = []
        for attempt in range(_MAX_RETRIES):
            try:
                verdicts = await batch_is_high_quality(texts)
                stats["llm_calls"] += 1
                break
            except Exception as exc:  # noqa: BLE001
                err      = str(exc)
                exc_name = type(exc).__name__

                is_rate   = "RateLimitError" in exc_name or "429" in err or "per-min" in err or "per-day" in err
                is_server = "InternalServerError" in exc_name or "500" in err
                is_not_found = "NotFoundError" in exc_name or "404" in err
                is_retryable = (is_rate or is_server) and not is_not_found

                wait = (5.0  if is_server
                        else _parse_rate_limit_reset(err, fallback=30.0) if is_rate
                        else 0.0)

                if attempt < _MAX_RETRIES - 1 and is_retryable:
                    logger.warning(f"{source_type}_l3_retry",
                                   attempt=attempt + 1, wait_s=round(wait, 1),
                                   error_type=exc_name)
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"{source_type}_l3_batch_error",
                                 error=err[:120], error_type=exc_name)
                    break

        for (raw, clean, title, meta), passed in zip(batch, verdicts):
            if passed:
                stats["pass_l3"] += 1
                approved.append({**raw, "clean_content": clean})
                logger.info(f"{source_type}_approved",
                            source_url=raw.get("source_url"))
            else:
                logger.debug(f"{source_type}_reject_l3",
                             source_url=raw.get("source_url"))

    logger.info(f"{source_type}_pipeline_complete", **stats)

    if output_path and approved:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(approved, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("approved_saved", path=str(output_path), count=len(approved))

    return approved
