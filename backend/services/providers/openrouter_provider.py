"""
OpenRouterProvider: envuelve la invocacion de OpenRouter como `ModelProvider`.

NOTA: Este proveedor ya no se usa en el flujo principal (Vertex AI exclusivo).
Se mantiene por compatibilidad con scripts de prueba y código heredado.
Los helpers se definen localmente en lugar de importarse de `ai_service`.

Feature: genia-agent-platform (Tarea 2.3)
"""

import asyncio
import json
import logging

import httpx

from config import settings
from services.providers.base import (
    GenerationRequest,
    GenerationResult,
    ModelProvider,
    ProviderError,
    ProviderTimeout,
)

logger = logging.getLogger(__name__)

DEFAULT_OPENROUTER_MODEL = "deepseek/deepseek-chat"


async def _post_openrouter_with_retries(
    client: httpx.AsyncClient, payload: dict, max_retries: int = 3
) -> httpx.Response:
    """POST a OpenRouter con reintentos para errores transitorios."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://genia.plataforma",
        "X-Title": "Plataforma Genia",
        "Content-Type": "application/json",
    }
    for attempt in range(max_retries):
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            if response.status_code == 429 or response.status_code >= 500:
                await asyncio.sleep(2 ** attempt)
                continue
            return response
        except (httpx.HTTPError, httpx.StreamError):
            await asyncio.sleep(2 ** attempt)
    raise Exception(f"OpenRouter no respondio tras {max_retries} intentos.")


def _message_to_dict(message) -> dict:
    """Convierte mensaje a dict."""
    return message if isinstance(message, dict) else {"role": message.role, "content": message.content}


class OpenRouterProvider(ModelProvider):
    """Proveedor de fallback: modelos servidos via OpenRouter."""

    name = "openrouter"

    def __init__(self, model: str | None = None):
        self.model = model or DEFAULT_OPENROUTER_MODEL

    def _build_messages(self, req: GenerationRequest) -> list[dict]:
        messages: list[dict] = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        messages.extend(req.messages)
        return [_message_to_dict(m) for m in messages]

    async def _call(self, req: GenerationRequest) -> GenerationResult:
        payload = {
            "model": self.model,
            "messages": self._build_messages(req),
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.tools:
            payload["tools"] = req.tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient() as client:
            response = await _post_openrouter_with_retries(client, payload)
            if response.status_code != 200:
                raise ProviderError(f"OpenRouter API error: {response.status_code}")
            data = response.json()

        choice = data["choices"][0]["message"]
        tool_calls = choice.get("tool_calls") or []

        usage = data.get("usage", {}) or {}
        return GenerationResult(
            text=choice.get("content") or "",
            provider_name=self.name,
            model=self.model,
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0) or 0,
            output_tokens=usage.get("completion_tokens", 0) or 0,
        )

    async def generate(
        self, req: GenerationRequest, timeout_s: float
    ) -> GenerationResult:
        """Genera con OpenRouter aplicando el timeout indicado."""
        if not settings.openrouter_api_key:
            raise ProviderError("OPENROUTER_API_KEY no esta configurado.")
        try:
            return await asyncio.wait_for(self._call(req), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            logger.warning("OpenRouterProvider: timeout tras %ss", timeout_s)
            raise ProviderTimeout(
                f"OpenRouter no respondio en {timeout_s}s"
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenRouterProvider: error de invocacion: %s", exc)
            raise ProviderError(f"OpenRouter error: {exc}") from exc
