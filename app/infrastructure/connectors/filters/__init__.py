"""Harvester filter modules — pure CPU, no I/O, no LLM (§4.1 compliant).

Naming convention: <source>_<layer>.py

X (Twitter) pipeline:
  Layer 1 — x_heuristic:         structural tweet quality gate.
  Layer 2 — x_text_cleaner:      noise removal (URLs, HTML, emoji runs).

YouTube Shorts pipeline:
  Layer 1 — yt_shorts_heuristic:  transcript existence + word count gate.
  Layer 2 — yt_text_cleaner:      strip [Music]/[Applause] tags, join fragments.

YouTube Long Video pipeline:
  Layer 1 — yt_long_heuristic:    segment word count gate (higher floor).
  Layer 2 — yt_text_cleaner:      same cleaner as Shorts (shared format).

Layer 3 (LLM) lives in app/application/services/filter_pipeline.py because
§4.1 forbids any LLM call inside the Harvester layer.
"""
