"""Layer 2 — Text cleaner (skills/text_cleaner).

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

# Matches http(s) URLs, bare www. and X's t.co shortlinks.
_URL_RE = re.compile(r"https?://\S+|www\.\S+|t\.co/\S+", re.IGNORECASE)

# Matches any HTML tag.
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Matches runs of 3+ consecutive Unicode emoji characters.
# Covers Emoticons (1F300–1F9FF), Misc Symbols (2600–27BF),
# Extended Pictographic (1FA00–1FA9F).
_EMOJI_RUN_RE = re.compile(
    r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FA9F]{3,}",
    flags=re.UNICODE,
)

# Collapses 2+ whitespace chars (including \n, \t) into a single space.
_WHITESPACE_RE = re.compile(r"\s{2,}")


def clean_noise(text: str) -> str:
    """Remove URLs, HTML, emoji runs, and excess whitespace.

    Hashtags and mentions are intentionally kept — Layer 1 already enforced
    their count limits, and they carry topical signal (e.g. "#Claude").

    Args:
        text: Raw tweet string, post-heuristic-filter.

    Returns:
        A clean, LLM-ready string. Returns an empty string if nothing
        meaningful remains after stripping.
    """
    # 1. Strip HTML tags first (before unescape to avoid double-processing).
    text = _HTML_TAG_RE.sub(" ", text)

    # 2. Decode HTML entities (&amp; → &, &lt; → <, numeric refs, etc.).
    text = html.unescape(text)

    # 3. Remove URLs — they add zero semantic value for a quality classifier.
    text = _URL_RE.sub("", text)

    # 4. Collapse emoji runs of 3+ down to a single ellipsis placeholder so
    #    the LLM still knows "there was expressive content here" without being
    #    overwhelmed by 🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀.
    text = _EMOJI_RUN_RE.sub("...", text)

    # 5. NFKC normalisation: collapses full-width ASCII, ligatures (ﬁ → fi),
    #    and other Unicode compatibility equivalents that confuse tokenisers.
    text = unicodedata.normalize("NFKC", text)

    # 6. Collapse whitespace / newlines introduced by the substitutions above.
    text = _WHITESPACE_RE.sub(" ", text).strip()

    return text
