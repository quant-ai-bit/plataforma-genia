"""
Modelo de Cuenta de Usuario para PLATAFORMA GENIA.

Gestiona roles (admin, user), estados de verificación (pending, active, rejected)
y la asignación selectiva de agentes de IA a cada cuenta.
"""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class UserAccount(Base):
    """
    Modelo ORM para cuentas de usuario sincronizadas con Supabase Auth.

    Attributes:
        id: UUID del usuario en Supabase Auth (clave primaria).
        email: Correo electrónico del usuario (único).
        role: Rol del usuario ('admin' o 'user').
        status: Estado de la cuenta ('pending', 'active', 'rejected').
        assigned_agent_id: ID del agente asignado por el administrador.
        created_at: Fecha de registro del usuario.
        updated_at: Fecha de última actualización.
        approved_at: Fecha en que el administrador aprobó la cuenta.
        approved_by: Correo o ID del administrador que autorizó la cuenta.
    """

    __tablename__ = "user_accounts"

    id = Column(
        String(255),
        primary_key=True,
        doc="UUID del usuario en Supabase Auth",
    )
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Correo electrónico registrado",
    )
    role = Column(
        String(20),
        default="user",
        nullable=False,
        doc="Rol de la cuenta: 'admin' o 'user'",
    )
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        doc="Estado de la cuenta: 'pending', 'active' o 'rejected'",
    )
    assigned_agent_id = Column(
        String(255),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID del agente de IA asignado a este usuario",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Fecha y hora de creación",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Fecha y hora de última modificación",
    )
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Fecha y hora en que fue autorizado",
    )
    approved_by = Column(
        String(255),
        nullable=True,
        doc="Correo del administrador que autorizó el acceso",
    )

    # Relación con el agente asignado
    assigned_agent = relationship(
        "Agent",
        foreign_keys=[assigned_agent_id],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<UserAccount(email={self.email!r}, role={self.role!r}, status={self.status!r}, agent_id={self.assigned_agent_id!r})>"
