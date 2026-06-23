"""
Modelo de API Key para autenticacion de la API publica multi-tenant.

Las API keys autentican las solicitudes a la API publica B2B (`/v1`).
Por seguridad solo se persiste el hash (SHA-256 + pepper) de la key;
el secreto en claro se entrega una unica vez al generarlo.
"""

import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from database import Base


class ApiKey(Base):
    """
    Modelo ORM para las API keys de los tenants.

    Attributes:
        id: Identificador unico (UUID hex).
        tenant_id: FK al tenant propietario de la key.
        key_hash: Hash de la API key (SHA-256 + pepper), nunca el texto plano.
        prefix: Primeros caracteres de la key para identificacion visual.
        revoked_at: Marca de tiempo de revocacion (null si esta activa).
        created_at: Fecha y hora de creacion.
    """

    __tablename__ = "api_key"

    id = Column(
        String,
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
        doc="Identificador unico UUID de la API key",
    )
    tenant_id = Column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del tenant propietario de la key",
    )
    key_hash = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        doc="Hash SHA-256 + pepper de la API key",
    )
    prefix = Column(
        String(20),
        nullable=True,
        doc="Primeros caracteres para identificacion visual",
    )
    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Marca de tiempo de revocacion (null si activa)",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Fecha y hora de creacion",
    )

    # --- Relacion ---
    tenant = relationship("Tenant", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id!r}, tenant={self.tenant_id!r}, prefix={self.prefix!r})>"
