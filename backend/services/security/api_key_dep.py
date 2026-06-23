"""
Dependencias de seguridad de la API publica `/v1`.

- `require_tenant`: lee la cabecera `X-API-Key`, la hashea (SHA-256 + pepper),
  busca una API key activa no revocada, resuelve el tenant propietario y verifica
  que este activo. Rechaza con 401 ante cualquier fallo.
- `enforce_subscription`: a partir del tenant resuelto, consulta su Subscription
  y aplica enforcement: 402 si la suscripcion esta inactiva/impaga/cancelada y
  429 si el uso acumulado del periodo supera el limite del plan.

El limite por plan se resuelve con `over_limit`, un helper simple y configurable
basado en el consumo agregado de `agent_usages` por periodo. Es un placeholder
ajustable hasta que el `billing_service` (Tarea 9.x) defina los limites reales.

Feature: genia-agent-platform (Tarea 3.3)
"""

import logging
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.agent_usage import AgentUsage
from models.subscription import Subscription
from models.tenant import Tenant
from services import apikey_service, tenant_service

logger = logging.getLogger(__name__)

# Estados de suscripcion que bloquean el acceso a la API publica (HTTP 402).
INACTIVE_SUBSCRIPTION_STATUSES = {"past_due", "canceled", "cancelled", "unpaid", "inactive"}

# Limite de tokens por periodo segun el plan (placeholder configurable).
# `None` significa sin limite. El plan no reconocido usa `DEFAULT_PLAN_LIMIT`.
PLAN_TOKEN_LIMITS: dict[str, int | None] = {
    "free": 100_000,
    "basic": 1_000_000,
    "pro": 10_000_000,
    "enterprise": None,
}
DEFAULT_PLAN_LIMIT: int | None = 1_000_000


def _current_period() -> str:
    """Devuelve el periodo de facturacion actual en formato `YYYY-MM` (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def plan_limit(plan: str | None) -> int | None:
    """
    Resuelve el limite de tokens del plan.

    Args:
        plan: Nombre del plan de la suscripcion.

    Returns:
        El limite de tokens del plan, o `None` si el plan no tiene limite.
    """
    if plan and plan in PLAN_TOKEN_LIMITS:
        return PLAN_TOKEN_LIMITS[plan]
    return DEFAULT_PLAN_LIMIT


def over_limit(db: Session, tenant_id: str, plan: str | None, period: str | None = None) -> bool:
    """
    Indica si el uso acumulado del tenant en el periodo supera el limite del plan.

    Suma `total_tokens` de los `agent_usages` del tenant para el periodo indicado
    y lo compara con el limite del plan. Si el plan no tiene limite, nunca supera.

    Args:
        db: Sesion de base de datos.
        tenant_id: Identificador del tenant.
        plan: Plan de la suscripcion (define el limite).
        period: Periodo `YYYY-MM`; por defecto, el periodo actual.

    Returns:
        True si el consumo supera el limite del plan; False en caso contrario.
    """
    limit = plan_limit(plan)
    if limit is None:
        return False

    period = period or _current_period()
    total = (
        db.query(func.coalesce(func.sum(AgentUsage.total_tokens), 0))
        .filter(AgentUsage.tenant_id == tenant_id, AgentUsage.period == period)
        .scalar()
    )
    return int(total or 0) > limit


async def require_tenant(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Tenant:
    """
    Autentica la solicitud por API key y resuelve el tenant propietario.

    Args:
        x_api_key: Valor de la cabecera `X-API-Key`.
        db: Sesion de base de datos.

    Returns:
        El `Tenant` activo propietario de la API key.

    Raises:
        HTTPException: 401 si la key es invalida/revocada o el tenant no esta activo.
    """
    key_hash = apikey_service.hash_api_key(x_api_key)
    api_key = apikey_service.get_active_by_hash(db, key_hash)
    if api_key is None or api_key.revoked_at is not None:
        raise HTTPException(status_code=401, detail="API key invalida o revocada")

    tenant = tenant_service.get(db, api_key.tenant_id)
    if not tenant_service.is_active(tenant):
        raise HTTPException(status_code=401, detail="Tenant invalido o inactivo")

    return tenant


async def enforce_subscription(
    tenant: Tenant = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> Tenant:
    """
    Aplica enforcement de suscripcion y limite de uso sobre el tenant resuelto.

    Args:
        tenant: Tenant autenticado (inyectado por `require_tenant`).
        db: Sesion de base de datos.

    Returns:
        El mismo `Tenant` si la suscripcion esta activa y dentro de limites.

    Raises:
        HTTPException: 402 si la suscripcion esta inactiva/impaga/cancelada;
            429 si el uso acumulado supera el limite del plan.
    """
    subscription = (
        db.query(Subscription)
        .filter(Subscription.tenant_id == tenant.id)
        .first()
    )
    status = (subscription.status or "").lower() if subscription else None
    if subscription is None or status is None or status in INACTIVE_SUBSCRIPTION_STATUSES:
        raise HTTPException(status_code=402, detail="Suscripcion inactiva")

    if over_limit(db, tenant.id, subscription.plan):
        raise HTTPException(status_code=429, detail="Limite de uso excedido")

    return tenant