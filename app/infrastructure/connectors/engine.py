"""Harvester engine — the LLM-free orchestrator (Chặng 0).

Responsibilities (and nothing more):

1. **Auto-discover plugins.** Scan ``extractors/plugins/`` at runtime and build a
   ``{PLUGIN_TYPE: class}`` registry. The engine never imports a plugin by name
   (zero-hardcode rule), so adding a source = dropping one file.
2. **Run each source in isolation.** Every source is wrapped in try/except: a
   crashing plugin (e.g. X layout change) is logged and skipped; the rest
   keep running. The engine never goes down because of one bad source.
3. **Stamp & land.** Tag each item with ``{tenant_id, harvested_at}`` and write
   an immutable JSON envelope into the Raw Data Lake, partitioned per tenant.

Hard rule: **no LLM calls anywhere in this layer.** Data ingestion ≠ inference.
"""

from __future__ import annotations

import importlib
import json
import os
import pkgutil
import re
import time
from pathlib import Path
from typing import Any

import structlog
import yaml

from app.core.config import settings
from app.infrastructure.connectors.extractors import plugins as plugins_pkg
from app.infrastructure.connectors.extractors.base import BaseExtractor
from app.infrastructure.connectors.models import HarvestedItem, RawEnvelope, SourceConfig

logger = structlog.get_logger(__name__)

# ${VAR} placeholders in YAML resolve from the environment — keeps secrets
# (e.g. X_AUTH_TOKEN) in .env, never in the tracked config file.
_ENV_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_env(value: Any) -> Any:
    """Recursively expand ``${VAR}`` placeholders against ``os.environ``."""
    if isinstance(value, str):
        def _sub(match: re.Match[str]) -> str:
            name = match.group(1)
            resolved = os.environ.get(name)
            if resolved is None:
                logger.warning("env_placeholder_unset", var=name)
                return match.group(0)  # leave literal so the gap is visible
            return resolved

        return _ENV_PLACEHOLDER.sub(_sub, value)
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    return value


class HarvesterEngine:
    """Discovers plugins, runs configured sources, lands raw tagged data."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        data_lake_path: str | Path | None = None,
    ) -> None:
        self.config_path = Path(config_path or settings.HARVESTER_CONFIG_PATH)
        self.data_lake_path = Path(data_lake_path or settings.RAW_DATA_LAKE_PATH)
        self._registry: dict[str, type[BaseExtractor]] = {}

    # ── Plugin discovery ────────────────────────────────────────────────
    def discover_plugins(self) -> dict[str, type[BaseExtractor]]:
        """Auto-load every ``BaseExtractor`` subclass under ``plugins/``.

        A broken plugin *module* (import error) is logged and skipped so it can
        never block the rest of the registry.
        """
        registry: dict[str, type[BaseExtractor]] = {}
        for mod_info in pkgutil.iter_modules(
            plugins_pkg.__path__, plugins_pkg.__name__ + "."
        ):
            try:
                module = importlib.import_module(mod_info.name)
            except Exception as exc:  # noqa: BLE001 — one bad plugin must not crash discovery
                logger.error("plugin_import_failed", module=mod_info.name, error=str(exc))
                continue

            for attr in vars(module).values():
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseExtractor)
                    and attr is not BaseExtractor
                    and getattr(attr, "PLUGIN_TYPE", "")
                ):
                    if attr.PLUGIN_TYPE in registry:
                        logger.warning(
                            "plugin_type_collision",
                            plugin_type=attr.PLUGIN_TYPE,
                            keeping=registry[attr.PLUGIN_TYPE].__name__,
                            ignoring=attr.__name__,
                        )
                        continue
                    registry[attr.PLUGIN_TYPE] = attr

        self._registry = registry
        logger.info("plugins_discovered", count=len(registry), types=sorted(registry))
        return registry

    # ── Config loading ──────────────────────────────────────────────────
    def load_sources(self) -> list[SourceConfig]:
        """Parse ``scraper_config.yaml`` into validated :class:`SourceConfig`."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Harvester config not found: {self.config_path}")

        raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        sources_raw: list[dict[str, Any]] = raw.get("sources", [])
        sources: list[SourceConfig] = []
        for entry in sources_raw:
            try:
                sources.append(SourceConfig(**_resolve_env(entry)))
            except Exception as exc:  # noqa: BLE001 — malformed entry shouldn't abort the run
                logger.error("source_config_invalid", entry=entry, error=str(exc))
        return sources

    # ── Main run loop ───────────────────────────────────────────────────
    async def run(self) -> dict[str, Any]:
        """Run all enabled sources. Returns a per-source summary report."""
        if not self._registry:
            self.discover_plugins()

        sources = self.load_sources()
        report: dict[str, Any] = {"sources": [], "total_items": 0, "total_failures": 0}

        for source in sources:
            result = await self._run_source(source)
            report["sources"].append(result)
            report["total_items"] += result["items"]
            report["total_failures"] += 0 if result["status"] == "ok" else 1

        logger.info(
            "harvest_complete",
            sources=len(report["sources"]),
            total_items=report["total_items"],
            failures=report["total_failures"],
        )
        return report

    async def _run_source(self, source: SourceConfig) -> dict[str, Any]:
        """Execute one source with full fault isolation + tenant enforcement."""
        log = logger.bind(source=source.name, plugin_type=source.type)

        if not source.enabled:
            log.info("source_skipped_disabled")
            return {"source": source.name, "status": "skipped", "items": 0}

        # ── Tenant isolation gate: no tenant_id → discard (iron rule). ──
        if not source.tenant_id:
            log.error("source_discarded_missing_tenant_id")
            return {"source": source.name, "status": "discarded", "items": 0}

        extractor_cls = self._registry.get(source.type)
        if extractor_cls is None:
            log.error("plugin_type_unknown", available=sorted(self._registry))
            return {"source": source.name, "status": "unknown_plugin", "items": 0}

        # ── Fault isolation: a plugin crash is logged, never propagated. ──
        try:
            extractor = extractor_cls(source)
            items = await extractor.extract()
        except Exception as exc:  # noqa: BLE001 — isolate this source, keep the rest alive
            log.error("source_failed", error=str(exc), error_type=type(exc).__name__)
            return {"source": source.name, "status": "failed", "items": 0, "error": str(exc)}

        written = self._persist(source, items)
        log.info("source_ok", items=written)
        return {"source": source.name, "status": "ok", "items": written}

    # ── Raw Data Lake cleanup (TTL) ─────────────────────────────────────
    def cleanup(self, ttl_hours: int | None = None) -> dict[str, int]:
        """Delete files in the Raw Data Lake older than ``ttl_hours``.

        Removes both ``.json`` envelopes and any media files (``.mp4``,
        ``.webm``, ``.m4a``, …). After deletion, prunes empty directories.
        Returns a summary ``{deleted_files, deleted_dirs, skipped}``.

        Args:
            ttl_hours: Override the setting value. Pass 0 to disable.
        """
        effective_ttl = ttl_hours if ttl_hours is not None else settings.RAW_DATA_LAKE_TTL_HOURS
        if effective_ttl <= 0:
            logger.info("cleanup_skipped", reason="TTL disabled (RAW_DATA_LAKE_TTL_HOURS=0)")
            return {"deleted_files": 0, "deleted_dirs": 0, "skipped": 0}

        cutoff = time.time() - effective_ttl * 3600
        deleted_files = 0
        skipped = 0

        if not self.data_lake_path.exists():
            return {"deleted_files": 0, "deleted_dirs": 0, "skipped": 0}

        for file in self.data_lake_path.rglob("*"):
            if not file.is_file():
                continue
            try:
                if file.stat().st_mtime < cutoff:
                    file.unlink()
                    deleted_files += 1
                    logger.debug("cleanup_deleted", path=str(file))
                else:
                    skipped += 1
            except OSError as exc:
                logger.warning("cleanup_delete_failed", path=str(file), error=str(exc))

        # Prune directories that are now empty (deepest first).
        deleted_dirs = 0
        for directory in sorted(self.data_lake_path.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                try:
                    directory.rmdir()
                    deleted_dirs += 1
                except OSError:
                    pass

        logger.info(
            "cleanup_complete",
            ttl_hours=effective_ttl,
            deleted_files=deleted_files,
            deleted_dirs=deleted_dirs,
            skipped=skipped,
        )
        return {"deleted_files": deleted_files, "deleted_dirs": deleted_dirs, "skipped": skipped}

    # ── Raw Data Lake persistence ───────────────────────────────────────
    def _persist(self, source: SourceConfig, items: list[HarvestedItem]) -> int:
        """Wrap each item with tenant context and write an immutable JSON file."""
        # tenant_id is guaranteed present by the caller's gate.
        assert source.tenant_id is not None
        target_dir = self.data_lake_path / source.tenant_id / source.type
        target_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for item in items:
            envelope = RawEnvelope(
                tenant_id=source.tenant_id,
                source_name=source.name,
                plugin_type=source.type,
                item=item,
            )
            out_file = target_dir / f"{envelope.harvest_id}.json"
            out_file.write_text(
                envelope.model_dump_json(indent=2), encoding="utf-8"
            )
            count += 1
        return count
