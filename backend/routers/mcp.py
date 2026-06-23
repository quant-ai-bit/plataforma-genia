"""
Router de gestión de servidores MCP para PLATAFORMA GENIA.

Permite agregar, listar, actualizar y eliminar configuraciones de
servidores MCP por agente, así como probar la conexión y descubrir
herramientas disponibles.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from models.mcp_server_config import MCPServerConfig
from services.mcp_client import mcp_client_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["MCP Servers"])


# ── Schemas Pydantic ─────────────────────────────────────────────────

class MCPServerCreate(BaseModel):
    """Schema para crear una configuración de servidor MCP."""
    agent_id: str = Field(..., description="ID del agente al que asociar el servidor.")
    name: str = Field(..., max_length=255, description="Nombre descriptivo del servidor.")
    server_type: str = Field(
        ...,
        pattern="^(stdio|sse)$",
        description="Tipo de servidor: 'stdio' o 'sse'.",
    )
    command: Optional[str] = Field(
        None, max_length=500, description="Comando para servidores stdio."
    )
    args: list[str] = Field(
        default_factory=list, description="Argumentos del comando stdio."
    )
    url: Optional[str] = Field(
        None, max_length=500, description="URL para servidores SSE."
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Variables de entorno para el servidor.",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Headers HTTP para servidores SSE.",
    )
    enabled: bool = Field(default=True, description="Si el servidor está habilitado.")


class MCPServerUpdate(BaseModel):
    """Schema para actualizar una configuración de servidor MCP."""
    name: Optional[str] = Field(None, max_length=255)
    command: Optional[str] = Field(None, max_length=500)
    args: Optional[list[str]] = None
    url: Optional[str] = Field(None, max_length=500)
    env_vars: Optional[dict[str, str]] = None
    headers: Optional[dict[str, str]] = None
    enabled: Optional[bool] = None


class MCPServerResponse(BaseModel):
    """Schema de respuesta para una configuración de servidor MCP."""
    id: str
    agent_id: str
    name: str
    server_type: str
    command: Optional[str] = None
    args: list[str] = []
    url: Optional[str] = None
    env_vars: dict[str, str] = {}
    headers: dict[str, str] = {}
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class MCPToolInfo(BaseModel):
    """Schema para información de una herramienta MCP descubierta."""
    name: str
    description: str = ""
    input_schema: dict = {}


class MCPTestResponse(BaseModel):
    """Schema de respuesta para prueba de conexión MCP."""
    success: bool
    message: str
    tools: list[MCPToolInfo] = []


# ── Endpoints ────────────────────────────────────────────────────────

@router.get(
    "/agents/{agent_id}/servers",
    response_model=list[MCPServerResponse],
)
def list_mcp_servers(agent_id: str, db: Session = Depends(get_db)):
    """Lista todos los servidores MCP configurados para un agente."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente con ID '{agent_id}' no encontrado.",
        )

    configs = (
        db.query(MCPServerConfig)
        .filter(MCPServerConfig.agent_id == agent_id)
        .order_by(MCPServerConfig.created_at.desc())
        .all()
    )
    return configs


@router.post(
    "/servers",
    response_model=MCPServerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mcp_server(data: MCPServerCreate, db: Session = Depends(get_db)):
    """Crea una nueva configuración de servidor MCP para un agente."""
    # Validar que el agente exista
    agent = db.query(Agent).filter(Agent.id == data.agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente con ID '{data.agent_id}' no encontrado.",
        )

    # Validar campos según tipo de servidor
    if data.server_type == "stdio" and not data.command:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los servidores de tipo 'stdio' requieren un 'command'.",
        )
    if data.server_type == "sse" and not data.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los servidores de tipo 'sse' requieren una 'url'.",
        )

    config = MCPServerConfig(
        agent_id=data.agent_id,
        name=data.name,
        server_type=data.server_type,
        command=data.command,
        args=data.args,
        url=data.url,
        env_vars=data.env_vars,
        headers=data.headers,
        enabled=data.enabled,
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    logger.info(
        "Servidor MCP '%s' (%s) creado para agente '%s'.",
        config.name,
        config.server_type,
        config.agent_id,
    )
    return config


@router.put("/servers/{server_id}", response_model=MCPServerResponse)
def update_mcp_server(
    server_id: str,
    data: MCPServerUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza una configuración de servidor MCP existente."""
    config = (
        db.query(MCPServerConfig)
        .filter(MCPServerConfig.id == server_id)
        .first()
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración MCP con ID '{server_id}' no encontrada.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)

    # Invalidar caché del cliente MCP
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(
                mcp_client_manager.disconnect_server(config.agent_id, server_id)
            )
        else:
            asyncio.run(
                mcp_client_manager.disconnect_server(config.agent_id, server_id)
            )
    except Exception:
        pass

    return config


@router.delete("/servers/{server_id}", status_code=status.HTTP_200_OK)
def delete_mcp_server(server_id: str, db: Session = Depends(get_db)):
    """Elimina una configuración de servidor MCP."""
    config = (
        db.query(MCPServerConfig)
        .filter(MCPServerConfig.id == server_id)
        .first()
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración MCP con ID '{server_id}' no encontrada.",
        )

    agent_id = config.agent_id

    # Invalidar caché del cliente MCP
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(
                mcp_client_manager.disconnect_server(agent_id, server_id)
            )
        else:
            asyncio.run(
                mcp_client_manager.disconnect_server(agent_id, server_id)
            )
    except Exception:
        pass

    db.delete(config)
    db.commit()

    return {
        "status": "success",
        "message": f"Servidor MCP '{server_id}' eliminado exitosamente.",
    }


@router.post("/servers/{server_id}/test", response_model=MCPTestResponse)
async def test_mcp_server(server_id: str, db: Session = Depends(get_db)):
    """
    Prueba la conexión a un servidor MCP y descubre las herramientas disponibles.
    """
    config = (
        db.query(MCPServerConfig)
        .filter(MCPServerConfig.id == server_id)
        .first()
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración MCP con ID '{server_id}' no encontrada.",
        )

    try:
        tools = await mcp_client_manager.connect_to_server(
            agent_id=config.agent_id,
            config_id=config.id,
            server_type=config.server_type,
            command=config.command,
            args=config.args,
            url=config.url,
            env_vars=config.env_vars,
            headers=config.headers,
        )

        tool_infos = [
            MCPToolInfo(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in tools
        ]

        return MCPTestResponse(
            success=True,
            message=f"Conexión exitosa. {len(tools)} herramientas descubiertas.",
            tools=tool_infos,
        )

    except Exception as e:
        logger.error(
            "Error al probar servidor MCP '%s': %s",
            server_id,
            str(e),
            exc_info=True,
        )
        return MCPTestResponse(
            success=False,
            message=f"Error de conexión: {str(e)}",
            tools=[],
        )
