"""
Modelo de Payment (cobro Bre-B) por tenant.

Representa un cobro individual generado para un tenant que se paga mediante
transferencia Bre-B (llaves) y se confirma con un comprobante verificado por el
Agente de Verificacion de Pagos (vision Gemini). Sustituye el flujo de Stripe.

La idempotencia se garantiza con un indice unico (tenant_id, reference): un mismo
`reference` no puede repetirse dentro de un tenant y, una vez verificado, no se
reutiliza para acreditar dos veces.
"""

import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    JSON,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class Payment(Base):
    """
    Modelo ORM para un cobro Bre-B de un tenant.

    Attributes:
        id: Identificador unico (UUID hex).
        tenant_id: FK al tenant (indexado).
        reference: Referencia unica del cobro dentro del tenant (idempotencia).
        expected_amount: Monto esperado en la moneda indicada (entero, sin decimales).
        currency: Moneda del cobro (por defecto 'COP').
        llave_destino: Llave Bre-B destino esperada (titular del cobro).
        status: Estado del cobro: pending/verified/rejected.
        comprobante_ref: Referencia/hash del comprobante usado (null hasta verificar).
        extracted: Datos extraidos del comprobante por vision (JSON, null hasta verificar).
        verified_at: Fecha y hora de verificacion (null hasta verificar).
        created_at: Fecha y hora de creacion.
    """

    __tablename__ = "payment"

    id = Column(
        String,
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
        doc="Identificador unico UUID del cobro",
    )
    tenant_id = Column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del tenant propietario del cobro",
    )
    reference = Column(
        String(255),
        nullable=False,
        doc="Referencia unica del cobro dentro del tenant (idempotencia)",
    )
    expected_amount = Column(
        Integer,
        nullable=False,
        doc="Monto esperado (entero, sin decimales) en la moneda del cobro",
    )
    currency = Column(
        String(3),
        nullable=False,
        default="COP",
        server_default="COP",
        doc="Moneda del cobro (ISO 4217); por defecto COP",
    )
    llave_destino = Column(
        String(255),
        nullable=False,
        doc="Llave Bre-B destino esperada (titular del cobro)",
    )
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
        doc="Estado del cobro: pending/verified/rejected",
    )
    comprobante_ref = Column(
        String(255),
        nullable=True,
        doc="Referencia/hash del comprobante verificado (null hasta verificar)",
    )
    extracted = Column(
        JSON,
        nullable=True,
        doc="Datos extraidos del comprobante por vision (null hasta verificar)",
    )
    reject_reason = Column(
        String(512),
        nullable=True,
        doc="Motivo del rechazo de la verificacion (null salvo status=rejected)",
    )
    verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Fecha y hora de verificacion (null hasta verificar)",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Fecha y hora de creacion",
    )

    # --- Restricciones ---
    __table_args__ = (
        UniqueConstraint("tenant_id", "reference", name="uq_payment_tenant_reference"),
    )

    # --- Relacion (unidireccional hacia Tenant) ---
    tenant = relationship("Tenant")

    def __repr__(self) -> str:
        return (
            f"<Payment(id={self.id!r}, tenant={self.tenant_id!r}, "
            f"reference={self.reference!r}, status={self.status!r})>"
        )