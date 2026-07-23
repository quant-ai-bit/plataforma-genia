"""
Model_Service: orquestador de Vertex AI (proveedor exclusivo) con
timeout, retry y monitoreo para PLATAFORMA GENIA.

Ya no itera entre proveedores de fallback — toda la generacion se delega
exclusivamente en Vertex AI (Google Cloud). El servicio aplica `model_timeout_s`
y `model_max_retries` sobre el unico proveedor disponible. Si falla, lanza
`ModelUnavailableError` (mapeable a HTTP 503).

El registro del consumo en el Usage_Record se delega en un `usage_ctx`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from config import settings as default_settings
from services.providers.base import (
    GenerationRequest,
    GenerationResult,
    ModelProvider,
    ModelUnavailableError,
    ProviderError,
    ProviderTimeout,
)

logger = logging.getLogger(__name__)


@dataclass
class UsageInfo:
    """
    Metadatos de consumo de una generacion resuelta por el Model_Service.

    Attributes:
        provider: Nombre del proveedor que finalmente atendio la solicitud.
        model: Identificador del modelo utilizado.
        input_tokens: Tokens de entrada consumidos.
        output_tokens: Tokens de salida generados.
        fallback: True si la solicitud se resolvio con un proveedor de fallback.
        fallback_reason: Motivo del fallback (error del proveedor previo) o None.
    """

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    fallback: bool
    fallback_reason: str | None


@runtime_checkable
class UsageRecorder(Protocol):
    """
    Contrato para registrar el consumo de una generacion en el Usage_Record.

    Cualquier objeto con un metodo `record(info)` sirve como contexto de uso.
    Esto desacopla el Model_Service de la capa de persistencia (DB).
    """

    def record(self, info: UsageInfo) -> None:  # pragma: no cover - protocolo
        ...


def build_providers_from_settings(settings=None) -> list[ModelProvider]:
    """
    Construye la lista de proveedores (solo Vertex AI).

    Args:
        settings: Objeto de configuracion (por defecto, el global `settings`).

    Returns:
        Lista con una unica instancia de `VertexAIProvider`.
    """
    settings = settings or default_settings

    from services.providers.vertex_provider import VertexAIProvider

    return [VertexAIProvider()]


class ModelService:
    """
    Orquesta la generacion entre varios proveedores con timeout/retry/fallback.

    Itera los proveedores en el orden recibido. Para cada uno reintenta hasta
    `max_retries` veces ante `ProviderTimeout`/`ProviderError`; si se agotan los
    reintentos, pasa al siguiente proveedor (fallback). El primer proveedor que
    responde con exito determina el resultado. Si todos fallan, se lanza
    `ModelUnavailableError`.
    """

    def __init__(self, providers: list[ModelProvider], settings=None):
        if not providers:
            raise ValueError("ModelService requiere al menos un proveedor.")
        settings = settings or default_settings
        self.providers = providers
        self.timeout: float = float(getattr(settings, "model_timeout_s", 30.0))
        self.max_retries: int = int(getattr(settings, "model_max_retries", 1))

    @classmethod
    def from_settings(cls, settings=None) -> "ModelService":
        """Factoria que construye el servicio y sus proveedores desde `Settings`."""
        settings = settings or default_settings
        return cls(build_providers_from_settings(settings), settings)

    async def generate(
        self,
        req: GenerationRequest,
        usage_ctx: UsageRecorder | None = None,
    ) -> GenerationResult:
        """
        Genera una respuesta probando los proveedores en orden con fallback.

        Args:
            req: Peticion de generacion.
            usage_ctx: Contexto opcional para registrar el consumo (Usage_Record).
                Si se provee, se invoca `usage_ctx.record(UsageInfo)` cuando un
                proveedor responde con exito.

        Returns:
            El `GenerationResult` del primer proveedor que respondio con exito.

        Raises:
            ModelUnavailableError: Si todos los proveedores fallan.
        """
        last_error: Exception | None = None

        for provider in self.providers:
            attempts = max(1, self.max_retries)
            for attempt in range(attempts):
                try:
                    result = await provider.generate(req, self.timeout)
                except (ProviderTimeout, ProviderError) as exc:
                    last_error = exc
                    logger.warning(
                        "Vertex AI fallo (intento %s/%s): %s",
                        attempt + 1,
                        attempts,
                        exc,
                    )
                    continue
                else:
                    self._record_usage(usage_ctx, result, fallback=False, reason=None)
                    return result

        detail = str(last_error) if last_error else "Vertex AI no disponible"
        logger.error("Vertex AI fallo definitivamente: %s", detail)
        raise ModelUnavailableError(detail=detail)

    @staticmethod
    def _record_usage(
        usage_ctx: UsageRecorder | None,
        result: GenerationResult,
        fallback: bool,
        reason: str | None,
    ) -> None:
        """Registra el consumo en el Usage_Record si hay contexto y sin propagar errores."""
        if usage_ctx is None:
            return
        info = UsageInfo(
            provider=result.provider_name,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            fallback=fallback,
            fallback_reason=reason,
        )
        try:
            usage_ctx.record(info)
        except Exception as exc:  # noqa: BLE001 - el registro no debe romper la respuesta
            logger.error("No se pudo registrar el Usage_Record: %s", exc)


class AgentUsageRecorder:
    """
    Recorder concreto que persiste el consumo en la tabla `agent_usages`.

    Acumula tokens/costo por (agente, modelo) y registra el proveedor realmente
    utilizado y, si hubo fallback, su motivo. Se construye con la sesion de DB y
    el `agent_id`/`tenant_id`, manteniendo el `ModelService` desacoplado de la DB.
    """

    def __init__(self, db, agent_id: str, tenant_id: str | None = None, period: str | None = None):
        self.db = db
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.period = period

    def _current_period(self) -> str:
        from datetime import datetime, timezone

        return self.period or datetime.now(timezone.utc).strftime("%Y-%m")

    def record(self, info: UsageInfo) -> None:
        """Crea o actualiza el `AgentUsage` del agente para el modelo utilizado."""
        from models.agent_usage import AgentUsage
        from services.ai_service import calculate_cost

        total_tokens = info.input_tokens + info.output_tokens
        cost = calculate_cost(info.model, info.input_tokens, info.output_tokens)
        period = self._current_period()

        usage = (
            self.db.query(AgentUsage)
            .filter(
                AgentUsage.agent_id == self.agent_id,
                AgentUsage.model == info.model,
                AgentUsage.period == period,
            )
            .first()
        )

        if usage is None:
            usage = AgentUsage(
                agent_id=self.agent_id,
                tenant_id=self.tenant_id,
                model=info.model,
                prompt_tokens=info.input_tokens,
                completion_tokens=info.output_tokens,
                total_tokens=total_tokens,
                cost=cost,
                model_provider=info.provider,
                fallback_reason=info.fallback_reason,
                period=period,
            )
            self.db.add(usage)
        else:
            usage.prompt_tokens = (usage.prompt_tokens or 0) + info.input_tokens
            usage.completion_tokens = (usage.completion_tokens or 0) + info.output_tokens
            usage.total_tokens = (usage.total_tokens or 0) + total_tokens
            usage.cost = (usage.cost or 0.0) + cost
            usage.model_provider = info.provider
            usage.fallback_reason = info.fallback_reason
            usage.period = period

        self.db.flush()