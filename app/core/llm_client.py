"""LLMClientBase — the single OpenAI-compat gateway for all LLM inference.

Architecture rule (§2, tech-stack-rule.md):
  No agent or service calls ``openai.*`` / ``anthropic.*`` directly.
  All inference flows through this class so the provider can be swapped at
  runtime via the three INFERENCE_* settings in .env:

    INFERENCE_PROVIDER = ollama          # local default
    INFERENCE_BASE_URL = http://localhost:11434/v1
    INFERENCE_MODEL    = hermes3
    INFERENCE_API_KEY  = ollama          # ignored by local providers

  Switching to OpenAI:
    INFERENCE_BASE_URL = https://api.openai.com/v1
    INFERENCE_MODEL    = gpt-4o-mini
    INFERENCE_API_KEY  = sk-...

  Switching to Mistral / any OpenAI-compat endpoint:
    INFERENCE_BASE_URL = https://api.mistral.ai/v1
    INFERENCE_MODEL    = mistral-small-latest
    INFERENCE_API_KEY  = <mistral key>

Usage::

    from app.core.llm_client import LLMClientBase

    llm = LLMClientBase()
    response = await llm.chat(system="You are ...", user="Evaluate: ...")
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings


class LLMClientBase:
    """Async wrapper around the OpenAI-compatible completions API.

    Instantiated once per service (module-level singleton pattern) — the
    underlying ``AsyncOpenAI`` client manages its own connection pool.
    """

    def __init__(self) -> None:
        # OpenRouter requires HTTP-Referer + X-Title headers on every request.
        # For Ollama / other local providers these headers are ignored.
        self._client = AsyncOpenAI(
            base_url=settings.INFERENCE_BASE_URL,
            api_key=settings.INFERENCE_API_KEY,
            default_headers={
                "HTTP-Referer": "https://github.com/nnkienn/n-assistant-core",
                "X-Title": "N Assistant Core",
            },
        )
        self.model: str = settings.INFERENCE_MODEL

    async def chat(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> str:
        """Single-turn chat completion. Returns the assistant message content.

        Args:
            system: The system prompt establishing role / behaviour.
            user: The user turn — the content to reason over.
            max_tokens: Cap on response length. Keep low for classifier calls.
            temperature: 0.0 for deterministic classifiers; higher for creative.

        Raises:
            openai.APIError: propagated to callers — never silently swallowed.
        """
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
