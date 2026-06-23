"""
Modelo de configuración de servidores MCP por agente.

Cada registro asocia un servidor MCP externo (o built-in) a un agente
específico, permitiendo configuración multi-tenant donde cada agente
puede tener su propio set de herramientas MCP.
"""

import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class MCPServerConfig(Base):
    """
    Modelo ORM para la configuración de servidores MCP asociados a un agente.

    Attributes:
        id: Identificador único (UUID hex).
        agent_id: FK al agente que posee esta configuración.
        name: Nombre descriptivo del servidor MCP (ej: "Google Calendar").
        server_type: Tipo de servidor: 'builtin' (tools nativos), 'stdio' o 'sse'.
        command: Comando para lanzar el servidor stdio (ej: "npx -y @anthropic-ai/mcp-server-google-maps").
        args: Argumentos adicionales para el comando (lista JSON).
        url: URL del servidor SSE (ej: "http://localhost:3001/sse").
        env_vars: Variables de entorno para el servidor (JSON dict, encriptado en producción).
        headers: Headers HTTP para servidores SSE (JSON dict).
        enabled: Si el servidor está habilitado para el agente.
        created_at: Fecha de creación.
        updated_at: Fecha de última actualización.
    """

    __tablename__ = "mcp_server_configs"

    id = Column(
        String,
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
        doc="Identificador único UUID de la configuración",
    )
    agent_id = Column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID del agente al que pertenece esta configuración",
    )
    tenant_id = Column(
        String,
        ForeignKey("tenant.id"),
        nullable=True,
        index=True,
        doc="ID del tenant propietario (multi-tenant). Nullable por compatibilidad.",
    )
    name = Column(
        String(255),
        nullable=False,
        doc="Nombre descriptivo del servidor MCP",
    )
    server_type = Column(
        String(20),
        nullable=False,
        default="builtin",
        doc="Tipo: 'builtin', 'stdio' o 'sse'",
    )
    command = Column(
        String(500),
        nullable=True,
        doc="Comando para servidor stdio (ej: 'npx -y @anthropic-ai/mcp-server-brave-search')",
    )
    args = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Argumentos adicionales para el comando stdio",
    )
    url = Column(
        String(500),
        nullable=True,
        doc="URL del servidor SSE",
    )
    env_vars = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Variables de entorno para el servidor (dict key-value)",
    )
    headers = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="Headers HTTP adicionales para servidores SSE",
    )
    enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Si el servidor está habilitado",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # --- Relación ---
    agent = relationship("Agent", back_populates="mcp_servers")

    def __repr__(self) -> str:
        return (
            f"<MCPServerConfig(id={self.id!r}, name={self.name!r}, "
            f"type={self.server_type!r}, agent={self.agent_id!r})>"
        )
