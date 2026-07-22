"""
VertexAIProvider: proveedor de Gemini via Vertex AI (Google Cloud).

Autenticacion leida exclusivamente de variables de entorno (nunca credenciales
incrustadas en codigo). Soporta DOS modos de credenciales de service account, mas
ADC como ultimo recurso:

  - GCP_SERVICE_ACCOUNT_JSON        -> contenido JSON del service account (ideal
                                       para Vercel / serverless). Se parsea con
                                       `service_account.Credentials.from_service_account_info`.
  - GOOGLE_APPLICATION_CREDENTIALS  -> ruta a un archivo JSON de service account
                                       (ideal en local).
  - (ninguna)                       -> Application Default Credentials (ADC) del
                                       entorno de ejecucion.

Otras variables:
  - GOOGLE_CLOUD_PROJECT            -> proyecto GCP (se infiere del JSON si falta)
  - GOOGLE_CLOUD_LOCATION           -> region (ej: us-central1)
  - VERTEX_GEMINI_MODEL             -> modelo (ej: gemini-1.5-pro)

El SDK de Vertex (`vertexai` / `google-cloud-aiplatform`) se importa de forma
diferida (lazy) para que el modulo pueda cargarse aunque el paquete no este
instalado en el entorno; el import real ocurre al invocar `generate`.

Feature: genia-agent-platform (Tarea 2.2)
"""

import asyncio
import json
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


class VertexAIProvider(ModelProvider):
    """Proveedor primario: Gemini ejecutado en Vertex AI (Google Cloud)."""

    name = "vertex"

    def __init__(self, model: str | None = None):
        self._initialized = False
        self.model_name = model or getattr(settings, "vertex_gemini_model", "") or "gemini-2.0-flash"
        self.project = getattr(settings, "google_cloud_project", "") or None
        self.location = getattr(settings, "google_cloud_location", "") or "us-central1"

    def _resolve_credentials(self):
        """
        Resuelve las credenciales de service account segun el entorno.

        Prioridad:
          1. `GCP_SERVICE_ACCOUNT_JSON` (contenido JSON; ideal para Vercel).
          2. `GOOGLE_APPLICATION_CREDENTIALS` (ruta a archivo; ideal en local).
          3. ADC (devuelve None y deja que el SDK resuelva las credenciales).

        Si el proyecto no esta configurado, intenta inferirlo del `project_id`
        del service account. Nunca registra el contenido de las credenciales.

        Returns:
            Un objeto `Credentials` o `None` (para ADC).
        """
        raw_json = getattr(settings, "gcp_service_account_json", "") or ""
        cred_path = getattr(settings, "google_application_credentials", "") or ""

        if raw_json.strip():
            try:
                from google.oauth2 import service_account  # import diferido

                info = json.loads(raw_json)
            except json.JSONDecodeError as exc:
                raise ProviderError(
                    "GCP_SERVICE_ACCOUNT_JSON no contiene un JSON valido."
                ) from exc
            except ImportError as exc:  # pragma: no cover - depende del entorno
                raise ProviderError(
                    "El paquete 'google-auth' no esta disponible para Vertex AI."
                ) from exc
            if not self.project:
                self.project = info.get("project_id") or self.project
            logger.info("Vertex AI: credenciales desde GCP_SERVICE_ACCOUNT_JSON (entorno).")
            return service_account.Credentials.from_service_account_info(info)

        if cred_path.strip():
            try:
                from google.oauth2 import service_account  # import diferido

                creds = service_account.Credentials.from_service_account_file(cred_path)
            except ImportError as exc:  # pragma: no cover - depende del entorno
                raise ProviderError(
                    "El paquete 'google-auth' no esta disponible para Vertex AI."
                ) from exc
            except Exception as exc:  # noqa: BLE001 - ruta invalida / archivo ilegible
                raise ProviderError(
                    f"No se pudo cargar GOOGLE_APPLICATION_CREDENTIALS: {exc}"
                ) from exc
            logger.info("Vertex AI: credenciales desde GOOGLE_APPLICATION_CREDENTIALS (archivo).")
            return creds

        logger.info("Vertex AI: usando Application Default Credentials (ADC).")
        return None

    def _ensure_init(self):
        """Inicializa el SDK de Vertex AI de forma diferida.

        Resuelve las credenciales (JSON en entorno, archivo o ADC) y llama a
        `vertexai.init` con el proyecto/region configurados.
        """
        if self._initialized:
            return
        try:
            import vertexai  # import diferido
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ProviderError(
                "El SDK de Vertex AI (google-cloud-aiplatform) no esta instalado."
            ) from exc

        credentials = self._resolve_credentials()

        if not self.project:
            raise ProviderError(
                "GOOGLE_CLOUD_PROJECT no esta configurado para Vertex AI."
            )

        vertexai.init(
            project=self.project,
            location=self.location,
            credentials=credentials,
        )
        self._initialized = True

    def _build_contents(self, req: GenerationRequest) -> list[str]:
        """Aplana los mensajes a texto para la invocacion de Gemini."""
        parts: list[str] = []
        for msg in req.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "") or ""
            if content:
                parts.append(f"{role}: {content}")
        return parts

    def _generate_sync(self, req: GenerationRequest) -> GenerationResult:
        """Invocacion sincrona de Gemini (ejecutada en un hilo)."""
        from vertexai.generative_models import GenerativeModel  # import diferido

        generation_config = {
            "max_output_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        model = GenerativeModel(
            self.model_name,
            system_instruction=req.system_prompt or None,
        )
        contents = self._build_contents(req)
        response = model.generate_content(
            contents,
            generation_config=generation_config,
        )

        text = getattr(response, "text", "") or ""

        input_tokens = 0
        output_tokens = 0
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
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
        """Genera con Gemini/Vertex aplicando el timeout indicado."""
        try:
            self._ensure_init()
            return await asyncio.wait_for(
                asyncio.to_thread(self._generate_sync, req),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError as exc:
            logger.warning("VertexAIProvider: timeout tras %ss", timeout_s)
            raise ProviderTimeout(
                f"Vertex AI no respondio en {timeout_s}s"
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - se normaliza a ProviderError
            logger.error("VertexAIProvider: error de invocacion: %s", exc)
            raise ProviderError(f"Vertex AI error: {exc}") from exc