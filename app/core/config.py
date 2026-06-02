"""Zero-hardcode application settings — loaded from environment / .env file.

Every tuneable knob is a pydantic-settings field. No magic strings scattered
across the codebase; import ``settings`` from here and use the typed attributes.

Usage::

    from app.core.config import settings
    print(settings.INFERENCE_MODEL)
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Root settings for n-assistant-core.

    Values are resolved in order:
      1. Environment variables (highest priority).
      2. ``.env`` file in project root (auto-loaded if present).
      3. Defaults declared below (lowest priority).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Inference provider ──────────────────────────────────────────────
    INFERENCE_PROVIDER: str = "ollama"
    INFERENCE_MODEL: str = "hermes3"
    INFERENCE_BASE_URL: str = "http://localhost:11434/v1"

    # ── Vector DB (Qdrant) ──────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6353"

    # ── Cache / Broker (Redis) ──────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6399/0"

    # ── Harvester engine (Chặng 0) ──────────────────────────────────────
    # Zero-hardcode: every scrape target lives in this YAML, never in code.
    HARVESTER_CONFIG_PATH: str = "scraper_config.yaml"
    # Immutable raw landing zone; partitioned per-tenant for isolation.
    RAW_DATA_LAKE_PATH: str = "raw_data_lake/texts"
    # Network etiquette for plugins that hit public HTTP endpoints.
    HARVESTER_USER_AGENT: str = "n-assistant-harvester/3.0 (+https://github.com/nnkienn/n-assistant-core)"
    HARVESTER_HTTP_TIMEOUT: float = 20.0
    # TLS verification for HTTP plugins. Keep True. Set False (or point a source's
    # `ca_bundle` at a CA file) only behind a TLS-intercepting proxy/firewall.
    HARVESTER_HTTP_VERIFY: bool = True
    # Auto-cleanup: delete raw data lake files older than this many hours.
    # 0 = disabled. Applies to both .json envelopes and downloaded media files.
    RAW_DATA_LAKE_TTL_HOURS: int = 72

    # ── Application ─────────────────────────────────────────────────────
    APP_NAME: str = "N Assistant — Core API (Open-Source)"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"


# Singleton — imported everywhere as ``from app.core.config import settings``
settings = Settings()
