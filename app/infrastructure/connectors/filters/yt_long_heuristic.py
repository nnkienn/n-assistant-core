"""Layer 1 — YouTube Long Video heuristic filter.

CRITICAL PERFORMANCE RULE
  This filter runs FIRST — before any text cleaning and before the LLM
  evaluator. Its cost is O(1) per item (pure string ops, no I/O).
  Only items that PASS this gate advance to Layer 2 → Layer 3.

Long video segments differ from Shorts:
  - ``content`` is a REAL transcript window, not a description.
  - Word count floor is higher — segments should contain substantive speech.
  - Title is less decisive: a mid-video segment titled "Episode 247" still
    has meaningful content; the transcript text is the primary signal.

Thresholds come from ``filter_config.youtube_long_heuristic`` in
config/scraper_config.yaml so they can be adjusted without touching code.

Public API
----------
    is_viable_long_segment(segment_text: str, config: dict) -> bool
"""

from __future__ import annotations


def is_viable_long_segment(segment_text: str | None, config: dict) -> bool:
    """Return True only when a transcript segment passes all heuristic checks.

    Checks are ordered cheapest-first (fail-fast):
      1. Text existence — empty or whitespace-only → discard.
      2. Word count floor — segment must contain enough substantive words.

    Args:
        segment_text: Raw transcript segment text (may be None or empty).
        config: The ``filter_config.youtube_long_heuristic`` mapping.
            Recognised keys (all optional):
              min_segment_words (int, default 40)

    Returns:
        True if the segment meets all thresholds; False to discard.
    """
    min_words: int = int(config.get("min_segment_words", 40))

    if not segment_text or not segment_text.strip():
        return False

    return len(segment_text.split()) >= min_words
