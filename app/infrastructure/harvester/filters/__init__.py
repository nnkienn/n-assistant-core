"""Harvester filter modules — pure CPU, no I/O, no LLM (§4.1 compliant).

Twitter (X) pipeline:
  Layer 1 — heuristic_filter:     structural tweet quality gate.
  Layer 2 — text_cleaner:         noise removal (URLs, HTML, emoji runs).

YouTube Shorts pipeline:
  Layer 1 — yt_heuristic_filter:  transcript existence + word count gate.
  Layer 2 — yt_text_cleaner:      strip [Music]/[Applause] tags, join fragments.

Layer 3 (LLM) lives in app/application/services/llm_evaluator.py because
§4.1 forbids any LLM call inside the Harvester layer.
"""
