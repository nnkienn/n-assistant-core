"""Layer 2 — X (Twitter) text cleaner.

Strips noise that wastes LLM tokens or degrades semantic quality:
  • URLs       — https/http/t.co links carry no meaning for a quality judge.
  • HTML tags  — some platforms include <b>, &amp;, etc. in their API responses.
  • Emoji runs — 1–2 emojis are fine context; 3+ consecutive emojis → placeholder.
  • Whitespace — collapses runs of spaces/newlines into a single space.

Pure string operations — no I/O, no network, no LLM. Safe to run inside the
Harvester layer (§4.1 compliant).

Public API
----------
    clean_noise(text: str) -> str
"""

from __future__ import annotations

import html
import re
import unicodedata

# ── Pre-compiled patterns ────────────────────────────────────────────────────

_URL_RE = re.compile(r"https?://\S+|www\.\S+|t\.co/\S+", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_EMOJI_RUN_RE = re.compile(
    r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FA9F]{3,}",
    flags=re.UNICODE,
)
_WHITESPACE_RE = re.compile(r"\s{2,}")


def clean_noise(text: str) -> str:
    """Remove URLs, HTML, emoji runs, and excess whitespace from a tweet.

    Hashtags and mentions are intentionally kept — Layer 1 already enforced
    their count limits, and they carry topical signal (e.g. "#Claude").

    Args:
        text: Raw tweet string, post-heuristic-filter.

    Returns:
        A clean, LLM-ready string. Returns an empty string if nothing
        meaningful remains after stripping.
    """
    text = _HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _URL_RE.sub("", text)
    text = _EMOJI_RUN_RE.sub("...", text)
    text = unicodedata.normalize("NFKC", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text
