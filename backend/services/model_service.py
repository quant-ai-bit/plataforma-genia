"""
Model_Service: orquestador de proveedores de modelo con timeout, retry y
fallback para PLATAFORMA GENIA.

Recibe una lista de `ModelProvider` ordenada segun `settings.model_fallback_order`
(por defecto: vertex, groq, openrouter) e itera sobre ella aplicando
`model_timeout_s` y `model_max_retries`. Ante un `ProviderTimeout` o
`ProviderError` pasa al siguiente proveedor (fallback). Si todos los proveedores
fallan, lanza `ModelUnavailableError` (mapeable a HTTP 503).

El registro del consumo en el Usage_Record (`agent_usages`) se delega en un
objeto de contexto (`usage_ctx`) inyectado por el llamador, de modo que el
servicio no se acopla directamente a la sesion de base de datos. Cuando hubo
fallback, se persiste tambien el motivo (`fallback_reason`).

Feature: genia-agent-platform (Tarea 2.4)
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
    Construye la lista ordenada de proveedores a partir de `Settings`.

    El orden se determina por `settings.model_fallback_order` (lista separada por
    comas, ej: "vertex,groq,openrouter"). Los nombres desconocidos se ignoran y
    se evitan duplicados manteniendo el primer orden de aparicion.

    Args:
        settings: Objeto de configuracion (por defecto, el global `settings`).

    Returns:
        Lista de instancias `ModelProvider` en el orden de fallback configurado.
    """
    settings = settings or default_settings

    # Import diferido para evitar ciclos y costo de import si no se usan.
    from services.providers.groq_provider import GroqProvider
    from services.providers.openrouter_provider import OpenRouterProvider
    from services.providers.vertex_provider import VertexAIProvider

    factories = {
        "vertex": VertexAIProvider,
        "groq": GroqProvider,
        "openrouter": OpenRouterProvider,
    }

    raw_order = getattr(settings, "model_fallback_order", "") or ""
    names = [n.strip().lower() for n in raw_order.split(",") if n.strip()]
    if not names:
        names = ["vertex", "groq", "openrouter"]

    providers: list[ModelProvider] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        factory = factories.get(name)
        if factory is None:
            logger.warning("Proveedor de modelo desconocido ignorado: %s", name)
            continue
        seen.add(name)
        providers.append(factory())

    if not providers:
        raise ValueError(
            "No se pudo construir ningun proveedor de modelo a partir de "
            "model_fallback_order."
        )
    return providers


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

        for idx, provider in enumerate(self.providers):
            attempts = max(1, self.max_retries)
            for attempt in range(attempts):
                try:
                    result = await provider.generate(req, self.timeout)
                except (ProviderTimeout, ProviderError) as exc:
                    last_error = exc
                    logger.warning(
                        "Proveedor '%s' fallo (intento %s/%s): %s",
                        provider.name,
                        attempt + 1,
                        attempts,
                        exc,
                    )
                    continue
                else:
                    fallback = idx > 0
                    reason = str(last_error) if (fallback and last_error) else None
                    self._record_usage(usage_ctx, result, fallback, reason)
                    if fallback:
                        logger.info(
                            "Generacion resuelta por fallback con '%s' (motivo: %s)",
                            provider.name,
                            reason,
                        )
                    return result

        detail = str(last_error) if last_error else "Sin proveedores disponibles"
        logger.error("Todos los proveedores de modelo fallaron: %s", detail)
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