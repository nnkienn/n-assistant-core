"""Chunker — split a document into retrieval-sized pieces.

Strategy (decided for this dataset, see Phase-2 notes)
------------------------------------------------------
- A document at or under ``max_words`` → ONE chunk (tweets and most YouTube
  segments land here; the harvester already pre-segmented transcripts to a
  sensible size, so we don't cut what's already the right size).
- Longer than that → pack whole sentences into ~``max_words`` chunks, repeating
  the last sentence(s) of each chunk at the start of the next (``overlap_words``)
  so an idea split across a seam isn't orphaned.

Why count WORDS, not TOKENS?
  bge-m3 thinks in tokens, but counting tokens means loading its tokenizer
  (extra cost + couples this pure function to the model). Words are a cheap
  proxy: ~1.3 tokens/word (EN), so ``max_words=400`` ≈ ~520 tokens — comfortably
  inside the 256–512 "sweet spot" and far under bge-m3's 8192 hard limit.

This is PURE logic — no I/O, no model — so it's trivially unit-testable.
"""

from __future__ import annotations

import re

# Split *after* a sentence-ending mark (Latin . ! ? and CJK 。！？) followed by
# whitespace. Lookbehind keeps the punctuation attached to the sentence.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+")


def _sentences(text: str) -> list[str]:
    """Naive sentence split — good enough for tweets + transcripts."""
    return [s for s in _SENTENCE_BOUNDARY.split(text.strip()) if s]


def _overlap_tail(sentences: list[str], overlap_words: int) -> list[str]:
    """Return the trailing sentences whose total words stay within overlap_words."""
    tail: list[str] = []
    count = 0
    for sentence in reversed(sentences):
        words = len(sentence.split())
        if tail and count + words > overlap_words:
            break
        tail.insert(0, sentence)
        count += words
    return tail


def chunk_text(text: str, *, max_words: int = 400, overlap_words: int = 60) -> list[str]:
    """Split ``text`` into chunks of roughly ``max_words`` words with overlap.

    Returns a list of chunk strings (in order). Empty input → empty list.
    """
    text = text.strip()
    if not text:
        return []

    # Short enough already → leave it as a single chunk (the common case here).
    if len(text.split()) <= max_words:
        return [text]

    # Too long → greedily pack sentences, carrying an overlap into each new chunk.
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in _sentences(text):
        words = len(sentence.split())
        # Adding this sentence would overflow → close the current chunk first.
        if current and current_words + words > max_words:
            chunks.append(" ".join(current))
            current = _overlap_tail(current, overlap_words)   # seed next chunk w/ overlap
            current_words = sum(len(s.split()) for s in current)
        current.append(sentence)
        current_words += words

    if current:
        chunks.append(" ".join(current))
    return chunks
