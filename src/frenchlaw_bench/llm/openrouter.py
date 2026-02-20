"""Client OpenRouter pour l'accès multi-modèle."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from frenchlaw_bench.config import OPENROUTER_API_KEY
from frenchlaw_bench.llm.base import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]


class OpenRouterClient(BaseLLMClient):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        provider: str | None = None,
        quantization: str | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key or OPENROUTER_API_KEY
        self._provider = provider
        self._quantization = quantization
        self._client = httpx.AsyncClient(timeout=300)

    async def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Provider routing (OpenRouter provider preferences)
        if self._provider or self._quantization:
            provider_prefs: dict = {}
            if self._provider:
                provider_prefs["order"] = [self._provider]
            if self._quantization:
                provider_prefs["quantizations"] = [self._quantization]
            payload["provider"] = provider_prefs
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(MAX_RETRIES):
            start = time.monotonic()
            resp = await self._client.post(OPENROUTER_URL, headers=headers, json=payload)

            if resp.status_code == 429 or resp.status_code >= 500:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                logger.warning(
                    "HTTP %d sur %s, retry %d/%d dans %ds",
                    resp.status_code, self.model, attempt + 1, MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
                continue

            resp.raise_for_status()
            elapsed = time.monotonic() - start

            data = resp.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})
            content = choice["message"].get("content") or ""

            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                latency_seconds=elapsed,
            )

        resp.raise_for_status()
        raise RuntimeError("Unreachable")

    async def close(self) -> None:
        await self._client.aclose()
