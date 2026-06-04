"""Layer 3 — Semantic LLM quality gate (skills/llm_evaluator).

BATCH DESIGN (token-efficient)
  Instead of 1 LLM call per tweet, batch_is_high_quality() sends N tweets in a
  single call and parses a comma-separated TRUE/FALSE list back.

  Cost comparison (OpenRouter free = 50 req/day):
    Before:  259 tweets → ~130 calls after L1 → exceeds 50/day limit
    After:   ~13 calls  (BATCH_SIZE=10) → well within 50/day limit

  Format contract with the LLM:
    User sends:   "1. <tweet>\n\n2. <tweet>\n\n..."
    LLM returns:  "TRUE,FALSE,TRUE,..."   (exactly N values, comma-separated)

Public API
----------
    batch_is_high_quality(texts: list[str]) -> list[bool]   ← use this
    is_high_quality_tech_news(text: str)    -> bool          ← single-call fallback
"""

from __future__ import annotations

import structlog

from app.core.llm_client import LLMClientBase

logger = structlog.get_logger(__name__)

BATCH_SIZE = 10  # tweets per LLM call — tune down if model struggles with format

# ── Prompts ───────────────────────────────────────────────────────────────────

_BATCH_SYSTEM_PROMPT = (
    "You are a content quality judge. "
    "For each numbered item below, decide if it is an informative, high-value "
    "tech/AI update suitable for a video script (TRUE) "
    "or spam, engagement bait, a joke, or a personal reply (FALSE).\n"
    "Return ONLY a comma-separated list of TRUE/FALSE in order — no spaces, "
    "no explanations, no numbering. Example for 3 items: TRUE,FALSE,TRUE"
)

_SINGLE_SYSTEM_PROMPT = (
    "You are a content quality judge. Analyze the text. "
    "Return exactly 'TRUE' if the text is an informative, high-value tech/AI "
    "update suitable for a video script. "
    "Return 'FALSE' if it is spam, engagement bait, a joke, or a personal reply."
)

_llm = LLMClientBase()


async def batch_is_high_quality(texts: list[str]) -> list[bool]:
    """Evaluate a batch of texts in ONE LLM call. Returns bool list, same order.

    Uses 1 API call regardless of batch size → 10× more quota-efficient than
    calling is_high_quality_tech_news() individually.

    Args:
        texts: List of clean (noise-stripped) tweet texts. Max BATCH_SIZE items.

    Returns:
        List of bools. Length always equals len(texts). On parse failure or
        length mismatch, the affected items default to False (conservative).
    """
    if not texts:
        return []

    numbered = "\n\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))

    raw = await _llm.chat(
        system=_BATCH_SYSTEM_PROMPT,
        user=numbered,
        max_tokens=len(texts) * 8,  # "TRUE," ≈ 6 chars; headroom for spacing
        temperature=0.0,
    )

    # Parse "TRUE,FALSE,TRUE,..." — strip punctuation that some models add
    parts = [p.strip().rstrip(".").upper() for p in raw.strip().split(",")]

    results: list[bool] = []
    for i in range(len(texts)):
        if i < len(parts):
            verdict = parts[i]
            passed = verdict == "TRUE"
            if verdict not in ("TRUE", "FALSE"):
                logger.warning("batch_unexpected_verdict", index=i, raw=verdict[:32])
            results.append(passed)
        else:
            # LLM returned fewer values than expected — conservative default
            logger.warning("batch_length_mismatch", expected=len(texts), got=len(parts))
            results.append(False)

    passes = sum(results)
    logger.info("batch_evaluated", batch_size=len(texts), passed=passes)
    return results


async def is_high_quality_tech_news(clean_text: str) -> bool:
    """Single-tweet fallback. Prefer batch_is_high_quality() for bulk runs."""
    raw_verdict = await _llm.chat(
        system=_SINGLE_SYSTEM_PROMPT,
        user=clean_text,
        max_tokens=8,
        temperature=0.0,
    )
    verdict = raw_verdict.strip().upper()
    log = logger.bind(verdict=verdict, text_preview=clean_text[:100])

    if verdict == "TRUE":
        log.info("llm_evaluator_pass")
        return True

    if verdict != "FALSE":
        log.warning("llm_evaluator_unexpected_verdict", raw=raw_verdict[:64])

    log.info("llm_evaluator_reject")
    return False
