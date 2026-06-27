"""Harvester engine (Chặng 0) — autonomous, LLM-free data acquisition.

Principle: *Data Ingestion ≠ Inference.* This subsystem only brings raw public
data home, tagged with ``tenant_id``. It never calls an LLM and never shares a
process with an Agent. See ``.agent/docs/master-execution-plan.md`` §Chặng 0
and ``product-requirements.md`` §3.8.
"""
