"""
Modelo de Tenant (cliente) para la plataforma multi-tenant.

Cada tenant representa un cliente B2B de la plataforma GENIA.
Todas las entidades de negocio (agentes, conocimiento, uso, acciones)
cuelgan de un tenant para garantizar el aislamiento de datos.
"""

import uuid

from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from database import Base


class Tenant(Base):
    """
    Modelo ORM para los tenants (clientes) de la plataforma.

    Attributes:
        id: Identificador unico (UUID hex).
        name: Nombre visible del tenant (ej: "con-tranqui").
        slug: Identificador unico legible usado para idempotencia.
        is_active: Si el tenant esta activo.
        created_at: Fecha y hora de creacion (UTC con zona horaria).
    """

    __tablename__ = "tenant"

    id = Column(
        String,
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
        doc="Identificador unico UUID del tenant",
    )
    name = Column(String(255), nullable=False, doc="Nombre del tenant")
    slug = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Slug unico del tenant (idempotencia)",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Si el tenant esta activo",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Fecha y hora de creacion",
    )

    # --- Relaciones ---
    api_keys = relationship(
        "ApiKey",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    subscription = relationship(
        "Subscription",
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )
    action_logs = relationship(
        "ActionLog",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id!r}, slug={self.slug!r}, active={self.is_active!r})>"
