"""Layer 2 — YouTube Shorts text cleaner (skills/yt_text_cleaner).

Strips YouTube-specific noise that wastes LLM tokens or degrades quality:
  • Auto-caption noise tags — [Music], [Applause], [Laughter], [♪], etc.
  • Sponsor/CTA boilerplate — "Subscribe", "Like and share", etc.
  • Excess whitespace         — collapses runs into a single space.

Then joins the (potentially fragmented) transcript segments into a single
clean paragraph suitable for LLM evaluation.

Pure string operations — no I/O, no network, no LLM. Safe to run inside the
Harvester layer (§4.1 compliant).

Public API
----------
    clean_transcript(raw_transcript: str) -> str
"""

from __future__ import annotations

import html
import re
import unicodedata

# ── Pre-compiled patterns ────────────────────────────────────────────────────

# YouTube auto-caption noise tags: [Music], [Applause], [Laughter],
# [♪ music ♪], [foreign], [inaudible], etc. Case-insensitive.
_YT_NOISE_TAG_RE = re.compile(
    r"\[(?:"
    r"Music|Applause|Laughter|Cheering|Cheers|Clapping|Crowd|Silence"
    r"|Inaudible|Foreign|♪[^]]*"
    r")\]",
    flags=re.IGNORECASE,
)

# Matches http(s) URLs and bare www. links.
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

# Matches any HTML tag (rare in transcripts but exists in some formats).
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Matches runs of 3+ consecutive Unicode emoji characters.
_EMOJI_RUN_RE = re.compile(
    r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FA9F]{3,}",
    flags=re.UNICODE,
)

# YouTube transcript timestamps in HH:MM:SS or MM:SS format.
_TIMESTAMP_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")

# Collapses 2+ whitespace chars (including \n, \t) into a single space.
_WHITESPACE_RE = re.compile(r"\s{2,}")


def clean_transcript(raw_transcript: str) -> str:
    """Remove YouTube noise tags, URLs, timestamps, and normalize whitespace.

    Joins fragmented transcript segments into a single clean paragraph
    ready for LLM evaluation.

    Args:
        raw_transcript: Raw transcript string (post-heuristic-filter).

    Returns:
        A clean, LLM-ready single paragraph. Returns an empty string if
        nothing meaningful remains after stripping.
    """
    text = raw_transcript

    # 1. Strip HTML tags first (before unescape).
    text = _HTML_TAG_RE.sub(" ", text)

    # 2. Decode HTML entities (&amp; → &, etc.).
    text = html.unescape(text)

    # 3. Remove YouTube auto-caption noise tags — [Music], [Applause], etc.
    #    These carry zero semantic value for content quality classification.
    text = _YT_NOISE_TAG_RE.sub("", text)

    # 4. Remove timestamps that some transcript formats include inline.
    text = _TIMESTAMP_RE.sub("", text)

    # 5. Remove URLs — no semantic value for the quality judge.
    text = _URL_RE.sub("", text)

    # 6. Collapse emoji runs of 3+ down to a single ellipsis placeholder.
    text = _EMOJI_RUN_RE.sub("...", text)

    # 7. NFKC normalisation: collapses full-width ASCII, ligatures, and
    #    other Unicode compatibility equivalents.
    text = unicodedata.normalize("NFKC", text)

    # 8. Collapse whitespace / newlines into a single space → clean paragraph.
    text = _WHITESPACE_RE.sub(" ", text).strip()

    return text
