"""
Modelo de Subscription (suscripcion de billing) por tenant.

Representa la suscripcion mensual local de un tenant. La activacion la realiza
la verificacion de un comprobante Bre-B (ver `breb_payment_service`); ya no hay
pasarela externa. El estado de la suscripcion gobierna el enforcement de acceso
a la API publica. Las columnas `stripe_*` son legacy (sin uso) y se conservan
por compatibilidad de esquema (migraciones no destructivas).
"""

import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from database import Base


class Subscription(Base):
    """
    Modelo ORM para la suscripcion de billing de un tenant.

    Attributes:
        id: Identificador unico (UUID hex).
        tenant_id: FK al tenant (unico, relacion 1:1).
        stripe_customer_id: (legacy, sin uso) ID de customer de la antigua pasarela.
        stripe_subscription_id: (legacy, sin uso) ID de suscripcion de la antigua pasarela.
        plan: Plan contratado (define limites de uso).
        status: Estado: active/past_due/canceled/unpaid.
        current_period_start: Inicio del periodo de facturacion actual.
        current_period_end: Fin del periodo de facturacion actual.
    """

    __tablename__ = "subscription"

    id = Column(
        String,
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
        doc="Identificador unico UUID de la suscripcion",
    )
    tenant_id = Column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="ID del tenant (relacion 1:1)",
    )
    stripe_customer_id = Column(
        String(255),
        nullable=True,
        doc="(legacy, sin uso) ID de customer de la antigua pasarela",
    )
    stripe_subscription_id = Column(
        String(255),
        nullable=True,
        doc="(legacy, sin uso) ID de suscripcion de la antigua pasarela",
    )
    plan = Column(
        String(100),
        nullable=True,
        doc="Plan contratado (define limites de uso)",
    )
    status = Column(
        String(50),
        nullable=True,
        doc="Estado: active/past_due/canceled/unpaid",
    )
    current_period_start = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Inicio del periodo de facturacion actual",
    )
    current_period_end = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Fin del periodo de facturacion actual",
    )

    # --- Relacion ---
    tenant = relationship("Tenant", back_populates="subscription")

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id!r}, tenant={self.tenant_id!r}, status={self.status!r})>"
