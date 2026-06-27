"""Layer 1 — X (Twitter) heuristic filter.

CRITICAL PERFORMANCE RULE
  This filter runs FIRST — before any thread-fetch network call and before the
  LLM evaluator. Its cost is O(1) per tweet (pure string regex, no I/O).
  Only tweets that PASS this gate advance to Layer 2 → Layer 3.
  Never reorder these layers: the expensive LLM call must never be wasted on
  a tweet that a 2 ms regex check would have rejected.

Thresholds come from ``filter_config.heuristic`` in config/scraper_config.yaml
so they can be adjusted without touching code (zero-hardcode rule).

Public API
----------
    is_clean_tweet(tweet_text: str, config: dict) -> bool
"""

from __future__ import annotations

import re

# Pre-compiled once at import time — re-use across millions of calls.
_HASHTAG_RE = re.compile(r"#\w+")
_MENTION_RE = re.compile(r"@\w+")

# CTA spam phrases — Discord shills, engagement bait, crypto culture.
_CTA_SPAM_RE = re.compile(
    r"\b(join\s+(our|my|the)\s+(discord|telegram|group|community|channel)"
    r"|follow\s+(for|us|me)\s+(more|back)"
    r"|link\s+in\s+(bio|profile)"
    r"|retweet\s+to\s+win"
    r"|drop\s+(your|a)\s+(wallet|address)"
    r"|^gm[!\s])"
    r"",
    flags=re.IGNORECASE,
)


def is_clean_tweet(tweet_text: str, config: dict) -> bool:
    """Return True only when the tweet passes all heuristic thresholds.

    Checks are ordered cheapest-first (fail-fast):
      1. @-reply opener  — single startswith() check
      2. Word count floor — one split()
      3. Hashtag count cap — regex findall
      4. Mention count cap — regex findall
      5. CTA spam detection — compiled regex search

    Args:
        tweet_text: Raw tweet content (before any cleaning).
        config: The ``filter_config.heuristic`` mapping from scraper_config.yaml.
            Recognised keys (all optional, defaults match the YAML spec):
              max_hashtags (int, default 3)
              min_words    (int, default 15)
              max_mentions (int, default 2)

    Returns:
        True if the tweet meets all thresholds; False to discard.
    """
    max_hashtags: int = int(config.get("max_hashtags", 3))
    min_words: int = int(config.get("min_words", 15))
    max_mentions: int = int(config.get("max_mentions", 2))

    stripped = tweet_text.strip()

    if stripped.startswith("@"):
        return False

    word_count = len(stripped.split())
    if word_count < min_words:
        return False

    hashtag_count = len(_HASHTAG_RE.findall(stripped))
    if hashtag_count > max_hashtags:
        return False

    mention_count = len(_MENTION_RE.findall(stripped))
    if mention_count > max_mentions:
        return False

    if _CTA_SPAM_RE.search(stripped):
        return False

    return True
