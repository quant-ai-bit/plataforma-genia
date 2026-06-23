"""
mcp_service: ejecucion auditada de MCP_Tools acotada por tenant.

Punto de entrada de alto nivel usado por la API publica `/v1` para invocar
herramientas MCP en nombre de un tenant. Reutiliza la infraestructura MCP
existente (`mcp_builtin_server`, `mcp_client_manager`) y la auditoria
(`action_log_service`).

Reglas (Requisitos 4.1-4.5, 7.3):
- Valida que la `MCP_Tool` este habilitada en el Agent_Config del tenant; si no
  lo esta, devuelve un `ToolResult` con estado `unavailable` (las herramientas
  built-in se consideran siempre disponibles).
- Crea un `Action_Log` al iniciar la invocacion y lo completa con el resultado.
- Invoca la herramienta con `scope=tenant.id` para garantizar que solo se actue
  sobre recursos del tenant que origino la solicitud.
- Ante un fallo registra el error en el `Action_Log` y devuelve estado `failed`.

Feature: genia-agent-platform (Tarea 7.2)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from models.agent import Agent
from models.mcp_server_config import MCPServerConfig
from services import action_log_service
from services.mcp_builtin_server import execute_builtin_tool, is_builtin_tool
from services.mcp_client import mcp_client_manager

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """
    Resultado de la invocacion de una MCP_Tool.

    Attributes:
        status: 'success', 'failed' o 'unavailable'.
        data: Datos devueltos por la herramienta (si exito).
        message: Mensaje legible (motivo de fallo/indisponibilidad).
        tool: Nombre de la herramienta invocada.
    """

    status: str
    data: dict | None = None
    message: str | None = None
    tool: str | None = None

    def summary(self) -> str:
        """Resumen corto para incluir en la respuesta de la API."""
        if self.status == "success":
            return f"Herramienta '{self.tool}' ejecutada correctamente."
        if self.status == "unavailable":
            return self.message or "Herramienta no disponible para el tenant."
        return self.message or "La herramienta fallo."


def _get_tenant_agent(db: Session, tenant_id: str) -> Agent | None:
    """Recupera el Agent_Config primario del tenant (acotado por tenant_id)."""
    return (
        db.query(Agent)
        .filter(Agent.tenant_id == tenant_id)
        .order_by(Agent.created_at.asc())
        .first()
    )


def _enabled_tools(agent: Agent | None) -> list[str]:
    """Lista de MCP_Tools habilitadas en el Agent_Config del tenant."""
    if agent is None:
        return []
    return list(agent.enabled_mcp_tools or [])


def _find_server_config_for_tool(db: Session, agent_id: str) -> MCPServerConfig | None:
    """
    Resuelve la configuracion del servidor MCP remoto del tenant.

    Devuelve el primer `MCPServerConfig` habilitado y no built-in del agente.
    El enrutamiento detallado por herramienta se afina en el aprovisionamiento.
    """
    return (
        db.query(MCPServerConfig)
        .filter(
            MCPServerConfig.agent_id == agent_id,
            MCPServerConfig.enabled == True,  # noqa: E712
            MCPServerConfig.server_type != "builtin",
        )
        .first()
    )


def _as_dict(result: Any) -> dict:
    """Normaliza el resultado de una herramienta a diccionario."""
    if isinstance(result, dict):
        return result
    return {"result": result}


async def _execute(
    db: Session,
    agent: Agent | None,
    tool_name: str,
    params: dict,
    scope: str,
    session_token: str | None = None,
    tenant_slug: str | None = None,
) -> dict:
    """Ejecuta la herramienta (built-in o servidor MCP remoto) con scope=tenant."""
    if is_builtin_tool(tool_name):
        return _as_dict(await execute_builtin_tool(tool_name, params))

    if agent is None:
        return {"error": "No hay Agent_Config para resolver el servidor MCP del tenant."}

    config = _find_server_config_for_tool(db, agent.id)
    if config is None:
        return {"error": f"No hay servidor MCP configurado para '{tool_name}'."}

    # Servidor MCP remoto HTTP (p.ej. con-tranqui): llamada saliente firmada.
    if config.server_type == "remote_http":
        return _as_dict(
            await mcp_client_manager.execute_remote_http(
                env_config=config.env_vars or {},
                tool_name=tool_name,
                arguments=params,
                session_token=session_token,
                tenant_slug=tenant_slug or scope,
            )
        )

    # Conexion (idempotente; usa cache de sesiones) y ejecucion con scope=tenant.
    await mcp_client_manager.connect_to_server(
        agent_id=agent.id,
        config_id=config.id,
        server_type=config.server_type,
        command=config.command,
        args=config.args,
        url=config.url,
        env_vars=config.env_vars,
        headers=config.headers,
    )
    result = await mcp_client_manager.execute_tool(
        agent_id=agent.id,
        config_id=config.id,
        tool_name=tool_name,
        arguments=params,
        scope=scope,
    )
    return _as_dict(result)


async def invoke(
    db: Session,
    tenant,
    tool_name: str,
    params: dict,
    agent: Agent | None = None,
    model_provider: str | None = None,
    scope: str | None = None,
    metadata: dict | None = None,
) -> ToolResult:
    """
    Invoca una MCP_Tool en nombre de un tenant con validacion y auditoria.

    Args:
        db: Sesion de base de datos.
        tenant: Tenant que origina la accion (debe tener `.id`).
        tool_name: Nombre de la MCP_Tool a invocar.
        params: Parametros de entrada de la herramienta.
        agent: Agent_Config del tenant (opcional; se resuelve si no se provee).
        model_provider: Proveedor de modelo que origino la accion (auditoria).
        scope: Ambito de la invocacion; por defecto `tenant.id`.

    Returns:
        `ToolResult` con estado success/failed/unavailable.
    """
    params = params or {}
    scope = scope or tenant.id
    session_token = (metadata or {}).get("session_token")
    if agent is None:
        agent = _get_tenant_agent(db, tenant.id)

    # 4.2 Validar habilitacion (las built-in se consideran siempre disponibles).
    if not is_builtin_tool(tool_name):
        if tool_name not in _enabled_tools(agent):
            logger.warning(
                "MCP_Tool '%s' no habilitada para el tenant %s.",
                tool_name,
                tenant.id,
            )
            log = await action_log_service.start(
                db,
                tenant_id=tenant.id,
                tool_name=tool_name,
                input_params=params,
                model_provider=model_provider,
            )
            await action_log_service.complete(
                db,
                log_id=log.id,
                status="unavailable",
                error="Tool not enabled for tenant",
            )
            return ToolResult(
                status="unavailable",
                message=f"Herramienta '{tool_name}' no habilitada para el tenant.",
                tool=tool_name,
            )

    # 4.3 Crear Action_Log al iniciar.
    log = await action_log_service.start(
        db,
        tenant_id=tenant.id,
        tool_name=tool_name,
        input_params=params,
        model_provider=model_provider,
    )

    try:
        result = await _execute(
            db,
            agent,
            tool_name,
            params,
            scope,
            session_token=session_token,
            tenant_slug=getattr(tenant, "slug", None),
        )
        if isinstance(result, dict) and result.get("error"):
            # 4.4 Fallo controlado devuelto por la herramienta.
            await action_log_service.complete(
                db, log_id=log.id, status="failed", error=str(result["error"])
            )
            return ToolResult(
                status="failed",
                message=str(result["error"]),
                data=result,
                tool=tool_name,
            )
        # Exito.
        await action_log_service.complete(
            db, log_id=log.id, status="success", result=result
        )
        return ToolResult(status="success", data=result, tool=tool_name)
    except Exception as exc:  # noqa: BLE001 - se audita y se devuelve failed
        logger.error("Fallo invocando MCP_Tool '%s': %s", tool_name, exc, exc_info=True)
        await action_log_service.complete(
            db, log_id=log.id, status="failed", error=str(exc)
        )
        return ToolResult(status="failed", message=str(exc), tool=tool_name)


