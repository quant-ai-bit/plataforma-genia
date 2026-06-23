"""
Modelo de Action_Log para auditoria de invocaciones de herramientas MCP.

Cada invocacion de una MCP_Tool por parte del agente genera un registro
de auditoria acotado al tenant, con parametros de entrada, resultado,
estado y proveedor de modelo que origino la accion.
"""

import uuid

from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship

from database import Base


class ActionLog(Base):
    """
    Modelo ORM para el registro de auditoria de acciones MCP.

    Attributes:
        id: Identificador unico (UUID hex).
        tenant_id: FK al tenant que origino la accion (indexado).
        tool_name: Nombre de la MCP_Tool invocada.
        input_params: Parametros de entrada (JSON).
        result: Resultado de la invocacion (JSON, null si fallo o pendiente).
        status: Estado: success/failed/unavailable.
        error: Mensaje de error si la invocacion fallo.
        model_provider: Proveedor de modelo que origino la accion.
        created_at: Fecha y hora de creacion (indexado para consulta por rango).
    """

    __tablename__ = "action_log"

    id = Column(
        String,
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
        doc="Identificador unico UUID del registro de accion",
    )
    tenant_id = Column(
        String,
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del tenant que origino la accion",
    )
    tool_name = Column(
        String(255),
        nullable=False,
        doc="Nombre de la MCP_Tool invocada",
    )
    input_params = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Parametros de entrada de la invocacion",
    )
    result = Column(
        JSON,
        nullable=True,
        doc="Resultado de la invocacion (null si fallo o pendiente)",
    )
    status = Column(
        String(50),
        nullable=False,
        doc="Estado: success/failed/unavailable",
    )
    error = Column(
        Text,
        nullable=True,
        doc="Mensaje de error si la invocacion fallo",
    )
    model_provider = Column(
        String(50),
        nullable=True,
        doc="Proveedor de modelo que origino la accion",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Fecha y hora de creacion (indexado por rango)",
    )

    # --- Relacion ---
    tenant = relationship("Tenant", back_populates="action_logs")

    def __repr__(self) -> str:
        return f"<ActionLog(id={self.id!r}, tenant={self.tenant_id!r}, tool={self.tool_name!r}, status={self.status!r})>"
