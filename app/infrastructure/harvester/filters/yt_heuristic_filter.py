"""Layer 1 — YouTube Shorts heuristic filter (skills/yt_heuristic_filter).

CRITICAL PERFORMANCE RULE
  This filter runs FIRST — before any text cleaning and before the LLM
  evaluator. Its cost is O(1) per item (pure string ops, no I/O).
  Only items that PASS this gate advance to Layer 2 → Layer 3.

YouTube Shorts differ from tweets:
  - Primary text signal is the *title* + *description*, not a tweet body.
  - A Short with no text at all (no title, no description) has zero signal.
  - Descriptions can be short or empty — the title alone often carries
    enough topical signal for the LLM judge to evaluate.

Thresholds come from ``filter_config.youtube_shorts_heuristic`` in
scraper_config.yaml so they can be adjusted without touching code.

Public API
----------
    is_viable_short(transcript: str | None, config: dict, *, title: str) -> bool
"""

from __future__ import annotations


def is_viable_short(
    transcript: str | None,
    config: dict,
    *,
    title: str = "",
) -> bool:
    """Return True only when the YouTube Short passes all heuristic checks.

    Checks are ordered cheapest-first (fail-fast):
      1. Text existence — both title AND transcript empty → Early Exit.
      2. Combined word count floor — title + transcript must meet threshold.

    Args:
        transcript: Raw transcript / description text (may be None).
        config: The ``filter_config.youtube_shorts_heuristic`` mapping.
            Recognised keys (all optional, defaults match the YAML spec):
              min_transcript_words (int, default 10)
        title: Video title (used in combined word count evaluation).

    Returns:
        True if the Short meets all thresholds; False to discard (Early Exit).
    """
    min_words: int = int(config.get("min_transcript_words", 10))

    # Build combined text signal from title + description.
    parts: list[str] = []
    if title and title.strip():
        parts.append(title.strip())
    if transcript and transcript.strip():
        parts.append(transcript.strip())

    # 1. No text at all — zero signal. Music-only, no title, nothing.
    if not parts:
        return False

    # 2. Combined word count floor — title + description together must carry
    #    enough substance for a quality evaluation.
    combined = " ".join(parts)
    word_count = len(combined.split())
    if word_count < min_words:
        return False

    return True
