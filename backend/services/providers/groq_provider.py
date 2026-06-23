"""
GroqProvider: envuelve la invocacion de Groq como `ModelProvider`.

Reutiliza el cliente Groq ya inicializado en `services.ai_service`
(`groq_client`) y normaliza la respuesta al DTO `GenerationResult`.

Feature: genia-agent-platform (Tarea 2.3)
"""

import asyncio
import logging

from config import settings
from services.providers.base import (
    GenerationRequest,
    GenerationResult,
    ModelProvider,
    ProviderError,
    ProviderTimeout,
)

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def _tool_call_to_dict(tc) -> dict:
    """Normaliza un tool_call del SDK de Groq a diccionario."""
    return {
        "id": getattr(tc, "id", None),
        "type": getattr(tc, "type", "function"),
        "function": {
            "name": tc.function.name,
            "arguments": tc.function.arguments,
        },
    }


class GroqProvider(ModelProvider):
    """Proveedor de fallback: modelos LLM servidos por Groq."""

    name = "groq"

    def __init__(self, model: str | None = None):
        self.model = model or DEFAULT_GROQ_MODEL

    def _build_messages(self, req: GenerationRequest) -> list[dict]:
        messages: list[dict] = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        messages.extend(req.messages)
        return messages

    async def _call(self, req: GenerationRequest) -> GenerationResult:
        # Reutiliza el cliente Groq inicializado en ai_service.
        from services.ai_service import groq_client

        kwargs = {
            "model": self.model,
            "messages": self._build_messages(req),
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.tools:
            kwargs["tools"] = req.tools
            kwargs["tool_choice"] = "auto"

        response = await groq_client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        tool_calls = []
        if getattr(message, "tool_calls", None):
            tool_calls = [_tool_call_to_dict(tc) for tc in message.tool_calls]

        input_tokens = 0
        output_tokens = 0
        if getattr(response, "usage", None):
            input_tokens = response.usage.prompt_tokens or 0
            output_tokens = response.usage.completion_tokens or 0

        return GenerationResult(
            text=message.content or "",
            provider_name=self.name,
            model=self.model,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def generate(
        self, req: GenerationRequest, timeout_s: float
    ) -> GenerationResult:
        """Genera con Groq aplicando el timeout indicado."""
        if not settings.groq_api_key:
            raise ProviderError("GROQ_API_KEY no esta configurado.")
        try:
            return await asyncio.wait_for(self._call(req), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            logger.warning("GroqProvider: timeout tras %ss", timeout_s)
            raise ProviderTimeout(f"Groq no respondio en {timeout_s}s") from exc
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("GroqProvider: error de invocacion: %s", exc)
            raise ProviderError(f"Groq error: {exc}") from exc
