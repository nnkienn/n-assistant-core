"""Data contracts for the Harvester engine.

Two pure models, no infrastructure dependencies:

* :class:`SourceConfig`  — one entry from ``scraper_config.yaml``. Carries the
  mandatory ``tenant_id`` and a free-form ``options`` bag so plugins stay
  zero-hardcode (URLs, selectors, limits all live in YAML).
* :class:`HarvestedItem` — a single unit a plugin brings back. Deliberately
  raw: just text + provenance. No embeddings, no LLM-derived fields — that is a
  later stage, not the Harvester's job.
* :class:`RawEnvelope`   — what actually lands in the Raw Data Lake: a
  :class:`HarvestedItem` wrapped with the engine-stamped ``tenant_id`` and
  ``harvested_at`` so the artifact is self-describing and immutable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceConfig(BaseModel):
    """One scrape target, parsed straight from ``scraper_config.yaml``."""

    name: str = Field(..., description="Human-readable unique id for the source.")
    type: str = Field(..., description="Plugin type key (matches BaseExtractor.PLUGIN_TYPE).")
    tenant_id: str | None = Field(
        default=None,
        description="MANDATORY tenant tag. Missing → the source is discarded.",
    )
    enabled: bool = True
    # Zero-hardcode bag: url, subreddit, selectors, limit, locale, cadence, ...
    options: dict[str, Any] = Field(default_factory=dict)


class HarvestedItem(BaseModel):
    """A single raw document returned by a plugin. LLM-free by construction."""

    source_url: str
    title: str = ""
    content: str = ""
    locale: str | None = None
    # Plugin-specific provenance (author, score, published_at, ...).
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawEnvelope(BaseModel):
    """Immutable Raw-Data-Lake record: item + engine-stamped tenant context."""

    harvest_id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    source_name: str
    plugin_type: str
    harvested_at: datetime = Field(default_factory=_utcnow)
    item: HarvestedItem
