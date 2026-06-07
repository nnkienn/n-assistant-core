"""Layer 3 — Semantic LLM quality gate (skills/llm_evaluator).

COST DESIGN (token-minimal, quality-neutral)
  The judge only emits TRUE/FALSE, so input tokens dominate. Four levers keep
  cost low **without** changing which items get approved:

    1. Verdict cache  — identical (model+prompt+text) is judged once, ever.
                        Re-runs over overlapping data cost 0 tokens.
    2. Input clipping — each item is trimmed to _JUDGE_CHAR_CAP chars; the
                        quality signal lives in the lead, not the tail.
    3. Batching       — BATCH_SIZE items per call amortizes the system prompt
                        (which xAI/OpenAI also prompt-cache automatically).
    4. Lean prompt    — minimal system prompt, output is a bare TRUE/FALSE list.

  Robustness: if the model returns the wrong COUNT, _judge() splits the batch
  and retries instead of defaulting the whole batch to FALSE — so a single
  malformed reply never silently drops good items (quality stays identical to
  one-item-per-call). Extra tokens are spent only on the rare mismatch.

  Format contract with the LLM:
    User sends:   "1. <item>\n\n2. <item>\n\n..."
    LLM returns:  "TRUE,FALSE,TRUE,..."   (exactly N values, comma-separated)

Public API
----------
    batch_is_high_quality(texts: list[str]) -> list[bool]   ← use this
    is_high_quality_tech_news(text: str)    -> bool          ← single-item helper
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import structlog

from app.core.llm_client import LLMClientBase

logger = structlog.get_logger(__name__)

BATCH_SIZE = 8  # items/call — amortizes the system prompt; non-reasoning model keeps it accurate

_JUDGE_CHAR_CAP = 500   # ~90 words — enough to judge quality, skips long-transcript tails
_PROMPT_VERSION = "v2"  # bump when the prompt changes → auto-invalidates cached verdicts

# Persisted verdict cache. Lives at the raw_data_lake root (bind-mounted, and
# outside RAW_DATA_LAKE_PATH=texts/ so the TTL cleanup never touches it).
_CACHE_PATH = Path(os.getenv("LLM_VERDICT_CACHE", "raw_data_lake/.llm_verdict_cache.json"))

# ── Prompt (lean; the example keeps the output format reliable) ────────────────

_BATCH_SYSTEM_PROMPT = (
    "Judge each numbered item. TRUE = informative, high-value tech/AI content "
    "worth a video script. FALSE = spam, engagement bait, joke, or personal reply. "
    "Output ONLY comma-separated TRUE/FALSE, one per item, in order — "
    "no spaces, no numbering, no extra text. Example for 3 items: TRUE,FALSE,TRUE"
)

_llm = LLMClientBase()

# ── Verdict cache ──────────────────────────────────────────────────────────────

_cache: dict[str, bool] | None = None


def _load_cache() -> dict[str, bool]:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — missing/corrupt file → start fresh
            _cache = {}
    return _cache


def _save_cache() -> None:
    if _cache is None:
        return
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(_cache), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — cache is best-effort, never fatal
        logger.warning("verdict_cache_save_failed", error=str(exc))


def _cache_key(text: str) -> str:
    """Key by model + prompt version + text, so changing any of them re-judges."""
    blob = f"{_llm.model}|{_PROMPT_VERSION}|{text}".encode("utf-8")
    return hashlib.sha1(blob).hexdigest()


# ── LLM call + parse ───────────────────────────────────────────────────────────

def _clip(text: str) -> str:
    return text if len(text) <= _JUDGE_CHAR_CAP else text[:_JUDGE_CHAR_CAP]


def _parse_verdicts(raw: str) -> list[bool]:
    """'TRUE,FALSE,' → [True, False]. Empty fragments dropped; non-TRUE → False."""
    return [
        frag.strip().rstrip(".").upper() == "TRUE"
        for frag in raw.strip().split(",")
        if frag.strip()
    ]


async def _judge(texts: list[str]) -> list[bool]:
    """LLM-judge a batch, guaranteeing len(result) == len(texts).

    On a count mismatch (model returned the wrong number of verdicts), the batch
    is split and retried rather than dropped — keeps quality identical to
    per-item calls while paying batch prices in the common case.
    """
    raw = await _llm.chat(
        system=_BATCH_SYSTEM_PROMPT,
        user="\n\n".join(f"{i + 1}. {_clip(t)}" for i, t in enumerate(texts)),
        max_tokens=len(texts) * 6,  # "TRUE," ≈ 2 tokens; ample headroom
        temperature=0.0,
    )
    verdicts = _parse_verdicts(raw)
    if len(verdicts) == len(texts):
        return verdicts

    if len(texts) == 1:
        logger.warning("judge_unparsable_single", raw=raw[:48])
        return [False]

    logger.warning("judge_count_mismatch_split", expected=len(texts), got=len(verdicts))
    mid = len(texts) // 2
    left = await _judge(texts[:mid])
    right = await _judge(texts[mid:])
    return left + right


# ── Public API ─────────────────────────────────────────────────────────────────

async def batch_is_high_quality(texts: list[str]) -> list[bool]:
    """Evaluate a batch of texts. Returns a bool list in the same order.

    Cache hits cost 0 tokens; only uncached items reach the LLM. Length always
    equals len(texts).

    Args:
        texts: Clean (noise-stripped) item texts. Up to BATCH_SIZE items.
    """
    if not texts:
        return []

    cache = _load_cache()
    results: list[bool | None] = [None] * len(texts)
    miss_idx: list[int] = []
    miss_txt: list[str] = []

    for i, t in enumerate(texts):
        key = _cache_key(t)
        if key in cache:
            results[i] = cache[key]
        else:
            miss_idx.append(i)
            miss_txt.append(t)

    if miss_txt:
        verdicts = await _judge(miss_txt)
        for j, verdict in enumerate(verdicts):
            i = miss_idx[j]
            results[i] = verdict
            cache[_cache_key(texts[i])] = verdict
        _save_cache()

    final = [bool(r) for r in results]
    logger.info(
        "batch_evaluated",
        total=len(texts),
        llm_judged=len(miss_txt),
        cache_hits=len(texts) - len(miss_txt),
        passed=sum(final),
    )
    return final


async def is_high_quality_tech_news(clean_text: str) -> bool:
    """Single-item helper. Shares the cache + parsing path of the batch API."""
    return (await batch_is_high_quality([clean_text]))[0]
