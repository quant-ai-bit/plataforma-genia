"""
GeminiProvider: envuelve la invocación directa de la API de Google Gemini (AI Studio)
como `ModelProvider` para PLATAFORMA GENIA.

Utiliza el API Key de Gemini (`settings.gemini_api_key`) y la biblioteca `google-generativeai`
que ya está instalada en el entorno.
"""

import asyncio
import logging
import google.generativeai as genai

from config import settings
from services.providers.base import (
    GenerationRequest,
    GenerationResult,
    ModelProvider,
    ProviderError,
    ProviderTimeout,
)

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


class GeminiProvider(ModelProvider):
    """Proveedor directo para los modelos de Google Gemini (AI Studio)."""

    name = "gemini"

    def __init__(self, model: str | None = None):
        self.model_name = model or DEFAULT_GEMINI_MODEL
        self._initialized = False

    def _ensure_init(self):
        """Asegura que el SDK esté configurado con la clave de API correcta."""
        if self._initialized:
            return
        if not settings.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY no está configurada.")
        genai.configure(api_key=settings.gemini_api_key)
        self._initialized = True

    def _build_contents(self, req: GenerationRequest) -> list[dict]:
        """Convierte la lista de mensajes al formato de contenido estructurado de Gemini.

        Gemini espera 'user' y 'model' (en lugar de 'assistant') y no acepta roles 'system'
        en la lista de contenidos.
        """
        contents = []
        for msg in req.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "") or ""
            
            if role == "system":
                # El prompt de sistema se pasa en la configuración del modelo, no aquí.
                continue
            
            # Normalizar roles para Gemini
            gemini_role = "user"
            if role in ("assistant", "model"):
                gemini_role = "model"
                
            contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })
        return contents

    async def _call(self, req: GenerationRequest) -> GenerationResult:
        self._ensure_init()

        generation_config = {
            "max_output_tokens": req.max_tokens,
            "temperature": req.temperature,
        }

        # Configurar system instruction
        system_instruction = req.system_prompt if req.system_prompt else None

        # Instanciar el modelo generativo
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction,
        )

        contents = self._build_contents(req)

        # La llamada sincrónica del SDK se ejecuta en un hilo de trabajo para no bloquear el bucle de eventos.
        def _sync_call():
            return model.generate_content(
                contents,
                generation_config=generation_config,
            )

        response = await asyncio.to_thread(_sync_call)

        text = response.text if response.text else ""

        # Leer estadísticas de tokens si están disponibles
        input_tokens = 0
        output_tokens = 0
        usage = getattr(response, "usage_metadata", None)
        if usage:
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0

        return GenerationResult(
            text=text,
            provider_name=self.name,
            model=self.model_name,
            tool_calls=[],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def generate(
        self, req: GenerationRequest, timeout_s: float
    ) -> GenerationResult:
        """Genera contenido con Gemini aplicando el timeout indicado."""
        try:
            return await asyncio.wait_for(self._call(req), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            logger.warning("GeminiProvider: timeout tras %ss", timeout_s)
            raise ProviderTimeout(f"Gemini no respondió en {timeout_s}s") from exc
        except ProviderError:
            raise
        except Exception as exc:
            logger.error("GeminiProvider: error de invocacion: %s", exc)
            raise ProviderError(f"Gemini error: {exc}") from exc
