"""The connection contract every Harvester plugin must honour.

Community contributors add a new source by dropping one file in
``extractors/plugins/`` that subclasses :class:`BaseExtractor` and sets a unique
:attr:`BaseExtractor.PLUGIN_TYPE`. The engine discovers it automatically — no
core code changes, no hardcoded imports (zero-hardcode rule).

Contract rules
--------------
* Set a unique ``PLUGIN_TYPE`` class attribute; it is the key sources reference
  via ``type:`` in ``scraper_config.yaml``.
* Implement async :meth:`extract` → return a list of :class:`HarvestedItem`.
* **Never** import or call an LLM here. The Harvester layer is inference-free.
* Read *everything* (URLs, selectors, limits, locale) from ``self.source.options``.
  Hardcoding a URL in a plugin is an architecture violation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from app.infrastructure.harvester.models import HarvestedItem, SourceConfig


class BaseExtractor(ABC):
    """Abstract base for all data-source plugins."""

    #: Unique discriminator. Subclasses MUST override with a non-empty string.
    PLUGIN_TYPE: ClassVar[str] = ""

    def __init__(self, source: SourceConfig) -> None:
        self.source = source

    @property
    def options(self) -> dict:
        """Convenience accessor for the zero-hardcode options bag from YAML."""
        return self.source.options

    def http_verify(self) -> bool | str:
        """Resolve the TLS-verify value for httpx (zero-hardcode).

        Precedence: per-source ``ca_bundle`` (a CA file path) → per-source
        ``verify`` → global ``HARVESTER_HTTP_VERIFY``. Defaults to secure (True).
        Only relax this behind a TLS-intercepting proxy/firewall.
        """
        from app.core.config import settings

        ca_bundle = self.options.get("ca_bundle")
        if ca_bundle:
            return str(ca_bundle)
        return bool(self.options.get("verify", settings.HARVESTER_HTTP_VERIFY))

    @abstractmethod
    async def extract(self) -> list[HarvestedItem]:
        """Fetch raw items for this source. Must not perform any LLM inference.

        Raise on failure — the engine isolates each plugin in try/except, so one
        plugin blowing up never takes down the others.
        """
        raise NotImplementedError
