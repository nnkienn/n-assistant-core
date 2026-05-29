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

    # ── Application ─────────────────────────────────────────────────────
    APP_NAME: str = "N Assistant — Core API (Open-Source)"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"


# Singleton — imported everywhere as ``from app.core.config import settings``
settings = Settings()
