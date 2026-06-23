"""
Registro MCP multi-tenant para PLATAFORMA GENIA.

Orquesta la combinación de herramientas built-in y externas para cada
agente, y gestiona la ejecución de herramientas independientemente
de su origen (built-in o servidor MCP externo).
"""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from services.mcp_builtin_server import (
    get_builtin_tools,
    execute_builtin_tool,
    is_builtin_tool,
)
from services.mcp_adapter import (
    mcp_tools_to_function_calling,
    function_call_to_mcp_request,
    mcp_result_to_tool_response,
)
from services.mcp_client import mcp_client_manager

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """
    Registro centralizado de herramientas MCP para PLATAFORMA GENIA.

    Combina:
    1. Herramientas built-in (save_lead, handoff, alert)
    2. Herramientas de servidores MCP externos (por agente)

    Y las expone en formato function-calling compatible con cualquier
    proveedor LLM.
    """

    async def get_tools_for_agent(
        self,
        db: Session,
        agent_id: str,
        custom_fields: list[dict] | None = None,
    ) -> tuple[list[dict], dict[str, str]]:
        """
        Obtiene todas las herramientas disponibles para un agente,
        combinando tools built-in y de servidores MCP externos.

        Args:
            db: Sesión de base de datos.
            agent_id: ID del agente.
            custom_fields: Campos personalizados del agente.

        Returns:
            Tupla (tools_function_calling, tool_origin_map):
            - tools_function_calling: Lista de tools en formato OpenAI/Groq.
            - tool_origin_map: Mapa {tool_name: server_config_id_or_"builtin"}.
        """
        all_mcp_tools: list[dict] = []
        tool_origin_map: dict[str, str] = {}

        # ── 1. Herramientas built-in ─────────────────────────────
        builtin_tools = get_builtin_tools(custom_fields)
        for tool in builtin_tools:
            all_mcp_tools.append(tool)
            tool_origin_map[tool["name"]] = "builtin"

        # ── 2. Herramientas de servidores MCP externos ───────────
        try:
            external_tools = await self._load_external_tools(db, agent_id)
            for tool in external_tools:
                # Evitar colisiones de nombre con tools built-in
                if tool["name"] in tool_origin_map:
                    logger.warning(
                        "Tool '%s' de servidor externo colisiona con built-in. "
                        "Prefijando con servidor.",
                        tool["name"],
                    )
                    server_id = tool.get("_mcp_server_id", "external")
                    tool["name"] = f"{server_id}__{tool['name']}"

                tool_origin_map[tool["name"]] = tool.get(
                    "_mcp_server_id", "external"
                )
                # Remover metadata interna antes de convertir
                clean_tool = {
                    k: v for k, v in tool.items() if not k.startswith("_")
                }
                all_mcp_tools.append(clean_tool)

        except Exception as e:
            logger.error(
                "Error cargando tools MCP externos para agente '%s': %s",
                agent_id,
                str(e),
                exc_info=True,
            )

        # ── 3. Convertir a formato function-calling ──────────────
        fc_tools = mcp_tools_to_function_calling(all_mcp_tools)

        logger.info(
            "Agente '%s': %d tools registrados (%d built-in, %d externos).",
            agent_id,
            len(fc_tools),
            len(builtin_tools),
            len(fc_tools) - len(builtin_tools),
        )

        return fc_tools, tool_origin_map

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        tool_origin_map: dict[str, str],
        agent_id: str,
        db: Session = None,
    ) -> dict[str, Any]:
        """
        Ejecuta una herramienta por nombre, delegando a built-in o
        servidor MCP externo según su origen. Valida que esté habilitada
        para el tenant del agente y registra la auditoría en ActionLog.
        """
        from models.agent import Agent
        from services.mcp_builtin_server import is_builtin_tool

        tenant_id = None
        agent_provider = None
        agent = None

        if db is not None:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                tenant_id = agent.tenant_id
                agent_provider = agent.provider

        # Validación de habilitación de herramienta si el agente pertenece a un tenant
        if tenant_id and not is_builtin_tool(tool_name):
            enabled_tools = agent.enabled_mcp_tools or []
            if tool_name not in enabled_tools:
                logger.warning(
                    "Herramienta '%s' no habilitada para el tenant %s (agente %s)",
                    tool_name,
                    tenant_id,
                    agent_id,
                )
                if db is not None:
                    from services import action_log_service
                    log = await action_log_service.start(
                        db,
                        tenant_id=tenant_id,
                        tool_name=tool_name,
                        input_params=arguments,
                        model_provider=agent_provider,
                    )
                    await action_log_service.complete(
                        db,
                        log_id=log.id,
                        status="unavailable",
                        error="Tool not enabled for tenant",
                    )
                return {
                    "error": f"Herramienta '{tool_name}' no habilitada para este tenant.",
                    "status": "unavailable"
                }

        # Registrar inicio en ActionLog si hay db y tenant
        log = None
        if db is not None and tenant_id:
            from services import action_log_service
            log = await action_log_service.start(
                db,
                tenant_id=tenant_id,
                tool_name=tool_name,
                input_params=arguments,
                model_provider=agent_provider,
            )

        origin = tool_origin_map.get(tool_name, "")

        try:
            if origin == "builtin" or is_builtin_tool(tool_name):
                # Ejecutar tool built-in
                result = await execute_builtin_tool(tool_name, arguments)
            elif origin:
                # Ejecutar en servidor MCP externo
                result = await mcp_client_manager.execute_tool(
                    agent_id=agent_id,
                    config_id=origin,
                    tool_name=tool_name,
                    arguments=arguments,
                    scope=tenant_id,
                )
            else:
                logger.warning(
                    "Herramienta '%s' no encontrada en el registro para agente '%s'.",
                    tool_name,
                    agent_id,
                )
                result = {"error": f"Herramienta '{tool_name}' no registrada."}

            # Registrar finalización en ActionLog
            if log is not None and db is not None:
                from services import action_log_service
                if isinstance(result, dict) and "error" in result:
                    await action_log_service.complete(
                        db,
                        log_id=log.id,
                        status="failed",
                        error=str(result["error"]),
                    )
                else:
                    await action_log_service.complete(
                        db,
                        log_id=log.id,
                        status="success",
                        result=result,
                    )
            return result

        except Exception as e:
            logger.error("Fallo ejecutando herramienta %s: %s", tool_name, str(e), exc_info=True)
            if log is not None and db is not None:
                from services import action_log_service
                await action_log_service.complete(
                    db,
                    log_id=log.id,
                    status="failed",
                    error=str(e),
                )
            return {"error": str(e)}

    async def _load_external_tools(
        self, db: Session, agent_id: str
    ) -> list[dict]:
        """
        Carga y conecta a los servidores MCP externos configurados
        para un agente, retornando todas sus herramientas.
        """
        from models.mcp_server_config import MCPServerConfig

        configs = (
            db.query(MCPServerConfig)
            .filter(
                MCPServerConfig.agent_id == agent_id,
                MCPServerConfig.enabled == True,
                MCPServerConfig.server_type != "builtin",
            )
            .all()
        )

        all_external_tools: list[dict] = []

        for config in configs:
            try:
                tools = await mcp_client_manager.connect_to_server(
                    agent_id=agent_id,
                    config_id=config.id,
                    server_type=config.server_type,
                    command=config.command,
                    args=config.args,
                    url=config.url,
                    env_vars=config.env_vars,
                    headers=config.headers,
                )

                # Enriquecer cada tool con el ID del servidor
                for tool in tools:
                    tool["_mcp_server_id"] = config.id

                all_external_tools.extend(tools)

                logger.info(
                    "Servidor MCP '%s' (%s) para agente '%s': %d tools cargados.",
                    config.name,
                    config.server_type,
                    agent_id,
                    len(tools),
                )

            except Exception as e:
                logger.error(
                    "Error conectando a servidor MCP '%s' para agente '%s': %s",
                    config.name,
                    agent_id,
                    str(e),
                )

        return all_external_tools


    async def register_remote(
        self,
        db: Session,
        tenant_id: str,
        url_env: str,
        service_token_env: str,
        tools: list[str] | None = None,
        name: str = "remote-mcp",
    ) -> "Any":
        """
        Registra (idempotente) el apuntador a un servidor MCP remoto del tenant.

        Crea o actualiza un `MCPServerConfig` de tipo `remote_http` asociado al
        Agent_Config del tenant. NO almacena secretos: solo guarda los NOMBRES
        de las variables de entorno (`url_env`, `service_token_env`) que se
        resuelven en tiempo de invocacion desde `Settings`/entorno, mas el
        catalogo de herramientas habilitadas. Idempotente por (agent, tipo
        remote_http): re-ejecutar no duplica la configuracion.

        Args:
            db: Sesion de base de datos.
            tenant_id: Identificador del tenant.
            url_env: Nombre de la env var con la URL base del MCP remoto.
            service_token_env: Nombre de la env var con el token de servicio.
            tools: Catalogo de herramientas habilitadas para el tenant.
            name: Nombre descriptivo del servidor MCP remoto.

        Returns:
            El `MCPServerConfig` creado o actualizado.
        """
        from models.agent import Agent
        from models.mcp_server_config import MCPServerConfig

        agent = (
            db.query(Agent)
            .filter(Agent.tenant_id == tenant_id)
            .order_by(Agent.created_at.asc())
            .first()
        )
        if agent is None:
            raise ValueError(
                "No hay Agent_Config para el tenant; registre el agente antes "
                "que el MCP remoto."
            )

        env_vars = {
            "url_env": url_env,
            "service_token_env": service_token_env,
            "enabled_tools": list(tools or []),
        }

        config = (
            db.query(MCPServerConfig)
            .filter(
                MCPServerConfig.agent_id == agent.id,
                MCPServerConfig.server_type == "remote_http",
            )
            .first()
        )
        if config is None:
            config = MCPServerConfig(
                agent_id=agent.id,
                tenant_id=tenant_id,
                name=name,
                server_type="remote_http",
                env_vars=env_vars,
                enabled=True,
            )
            db.add(config)
            logger.info(
                "MCP remoto registrado para tenant %s (url_env=%s)",
                tenant_id,
                url_env,
            )
        else:
            config.tenant_id = tenant_id
            config.name = name
            config.env_vars = env_vars
            config.enabled = True
            logger.info(
                "MCP remoto actualizado para tenant %s (url_env=%s)",
                tenant_id,
                url_env,
            )
        db.flush()
        return config

# ── Instancia global del registro ────────────────────────────────────
mcp_registry = MCPToolRegistry()

