"""
billing_service: gestion de suscripciones de PLATAFORMA GENIA.

Tras reemplazar Stripe por cobros Bre-B (ver `breb_payment_service`), este modulo
conserva exclusivamente la logica local de suscripciones, independiente de
cualquier pasarela externa:

- Persistencia y lectura de la entidad `Subscription` por `tenant_id`.
- `ensure_subscription`: asegura (idempotente) una suscripcion local para el
  aprovisionamiento.
- `upsert_subscription`: crea/actualiza la suscripcion (la activacion real la hace
  `breb_payment_service.verify_payment` al validar un comprobante Bre-B).
- `over_limit`: enforcement de uso a partir del consumo agregado en `agent_usages`
  por periodo.

La activacion de la suscripcion ya no proviene de webhooks de Stripe, sino de la
verificacion por vision (Gemini) de un comprobante Bre-B.

Feature: genia-agent-platform (Tareas 9.x - Cobros Bre-B)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.agent_usage import AgentUsage
from models.subscription import Subscription

logger = logging.getLogger(__name__)

# Estados de suscripcion que se consideran inactivos para el enforcement (402).
INACTIVE_SUBSCRIPTION_STATUSES = {
    "past_due",
    "canceled",
    "cancelled",
    "unpaid",
    "inactive",
}

# Limite de tokens por periodo segun el plan (placeholder configurable).
# `None` significa sin limite.
PLAN_TOKEN_LIMITS: dict[str, int | None] = {
    "free": 100_000,
    "basic": 1_000_000,
    "pro": 10_000_000,
    "enterprise": None,
}
DEFAULT_PLAN_LIMIT: int | None = 1_000_000


# ── Repositorio de Subscription ─────────────────────────────────────
def get_subscription(db: Session, tenant_id: str) -> Subscription | None:
    """Recupera la suscripcion de un tenant (relacion 1:1), acotada por tenant."""
    if not tenant_id:
        return None
    return (
        db.query(Subscription)
        .filter(Subscription.tenant_id == tenant_id)
        .first()
    )


def upsert_subscription(db: Session, tenant_id: str, **fields) -> Subscription:
    """
    Crea o actualiza la suscripcion del tenant con los campos provistos.

    Args:
        db: Sesion de base de datos.
        tenant_id: Identificador del tenant.
        **fields: Campos a establecer (plan, status, current_period_start,
            current_period_end, etc.).

    Returns:
        La fila `Subscription` persistida (acotada al tenant).
    """
    subscription = get_subscription(db, tenant_id)
    if subscription is None:
        subscription = Subscription(tenant_id=tenant_id)
        db.add(subscription)
    for key, value in fields.items():
        if value is not None and hasattr(subscription, key):
            setattr(subscription, key, value)
    db.flush()
    db.commit()
    logger.info(
        "Subscription upsert para tenant %s (status=%s, plan=%s)",
        tenant_id,
        getattr(subscription, "status", None),
        getattr(subscription, "plan", None),
    )
    return subscription


def ensure_subscription(
    db: Session, tenant_id: str, plan: str | None = None
) -> Subscription:
    """
    Asegura (idempotente) una suscripcion local para el tenant.

    Pensada para el aprovisionamiento: si el tenant ya tiene suscripcion la
    devuelve sin cambios; si no, crea una fila local con estado `active` y el
    plan indicado (por defecto, `default`). No realiza llamadas a pasarelas
    externas; la activacion real se hace al verificar un comprobante Bre-B.
    """
    subscription = get_subscription(db, tenant_id)
    if subscription is not None:
        return subscription
    plan = plan or "default"
    subscription = Subscription(
        tenant_id=tenant_id,
        plan=plan,
        status="active",
    )
    db.add(subscription)
    db.flush()
    logger.info("Subscription asegurada para tenant %s (plan=%s)", tenant_id, plan)
    return subscription


# ── Enforcement de uso ──────────────────────────────────────────────
def plan_limit(plan: str | None) -> int | None:
    """Resuelve el limite de tokens del plan (None = sin limite)."""
    if plan and plan in PLAN_TOKEN_LIMITS:
        return PLAN_TOKEN_LIMITS[plan]
    return DEFAULT_PLAN_LIMIT


def _current_period() -> str:
    """Periodo de facturacion actual en formato `YYYY-MM` (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def over_limit(
    db: Session, tenant_id: str, plan: str | None, period: str | None = None
) -> bool:
    """
    Indica si el uso acumulado del tenant en el periodo supera el limite del plan.

    Suma `total_tokens` de los `agent_usages` del tenant para el periodo y lo
    compara con el limite del plan. Si el plan no tiene limite, nunca supera.
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