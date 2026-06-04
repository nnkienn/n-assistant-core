"""Harvester filter modules — pure CPU, no I/O, no LLM (§4.1 compliant).

Layer 1 — heuristic_filter: structural tweet quality gate.
Layer 2 — text_cleaner:     noise removal (URLs, HTML, emoji runs).
Layer 3 (LLM) lives in app/application/services/llm_evaluator.py because
§4.1 forbids any LLM call inside the Harvester layer.
"""
