"""
Cliente MCP multi-tenant para PLATAFORMA GENIA.

Gestiona conexiones a servidores MCP externos por agente,
permitiendo que cada agente tenga su propio set de herramientas
MCP conectadas de forma independiente.
"""

import asyncio
import logging
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)


class MCPClientManager:
    """
    Gestor de conexiones MCP multi-tenant.

    Mantiene un caché de sesiones activas por agente y servidor,
    y proporciona métodos para descubrir y ejecutar herramientas
    en servidores MCP externos.
    """

    def __init__(self):
        """Inicializa el gestor con un caché de sesiones vacío."""
        # Caché: {agent_id: {server_config_id: {"session": ..., "tools": [...]}}}
        self._sessions: dict[str, dict[str, dict]] = {}
        self._lock = asyncio.Lock()

    async def connect_to_server(
        self,
        agent_id: str,
        config_id: str,
        server_type: str,
        command: str | None = None,
        args: list[str] | None = None,
        url: str | None = None,
        env_vars: dict | None = None,
        headers: dict | None = None,
    ) -> list[dict]:
        """
        Conecta a un servidor MCP y retorna sus herramientas disponibles.

        Args:
            agent_id: ID del agente.
            config_id: ID de la configuración del servidor.
            server_type: Tipo de servidor ('stdio' o 'sse').
            command: Comando para servidor stdio.
            args: Argumentos para el comando stdio.
            url: URL para servidor SSE.
            env_vars: Variables de entorno para el servidor.
            headers: Headers HTTP para servidor SSE.

        Returns:
            Lista de tools disponibles en formato MCP.
        """
        async with self._lock:
            # Verificar si ya existe una conexión activa
            if agent_id in self._sessions and config_id in self._sessions[agent_id]:
                cached = self._sessions[agent_id][config_id]
                if cached.get("tools"):
                    return cached["tools"]

        try:
            if server_type == "stdio":
                tools = await self._connect_stdio(
                    command=command or "",
                    args=args or [],
                    env_vars=env_vars or {},
                )
            elif server_type == "sse":
                tools = await self._connect_sse(
                    url=url or "",
                    headers=headers or {},
                )
            else:
                logger.warning(
                    "Tipo de servidor MCP '%s' no soportado.", server_type
                )
                return []

            # Cachear los tools descubiertos
            async with self._lock:
                if agent_id not in self._sessions:
                    self._sessions[agent_id] = {}
                self._sessions[agent_id][config_id] = {
                    "tools": tools,
                    "server_type": server_type,
                    "config": {
                        "command": command,
                        "args": args,
                        "url": url,
                        "env_vars": env_vars,
                        "headers": headers,
                    },
                }

            logger.info(
                "Conectado a servidor MCP '%s' para agente '%s'. %d tools disponibles.",
                config_id,
                agent_id,
                len(tools),
            )
            return tools

        except Exception as e:
            logger.error(
                "Error conectando a servidor MCP '%s' para agente '%s': %s",
                config_id,
                agent_id,
                str(e),
                exc_info=True,
            )
            return []

    async def _connect_stdio(
        self, command: str, args: list[str], env_vars: dict
    ) -> list[dict]:
        """Conecta a un servidor MCP via stdio y lista sus tools."""
        import os

        # Merge con las variables de entorno del sistema
        merged_env = {**os.environ, **env_vars}

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=merged_env,
        )

        tools = []
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                for tool in result.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
                    })
        return tools

    async def _connect_sse(
        self, url: str, headers: dict
    ) -> list[dict]:
        """Conecta a un servidor MCP via SSE y lista sus tools."""
        tools = []
        async with sse_client(url=url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                for tool in result.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
                    })
        return tools

    async def execute_tool(
        self,
        agent_id: str,
        config_id: str,
        tool_name: str,
        arguments: dict,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """
        Ejecuta una herramienta en un servidor MCP externo.

        Establece una nueva conexión para ejecutar el tool (stateless)
        para evitar problemas de sesiones caducadas.

        Args:
            agent_id: ID del agente.
            config_id: ID de la configuración del servidor.
            tool_name: Nombre de la herramienta a ejecutar.
            arguments: Argumentos para la herramienta.

        Returns:
            Diccionario con el resultado de la ejecución.
        """
        async with self._lock:
            server_info = self._sessions.get(agent_id, {}).get(config_id)

        if not server_info:
            return {"error": f"No hay sesión activa para el servidor '{config_id}' del agente '{agent_id}'."}

        config = server_info["config"]
        server_type = server_info["server_type"]

        try:
            if server_type == "stdio":
                return await self._execute_stdio(
                    command=config["command"],
                    args=config["args"] or [],
                    env_vars=config["env_vars"] or {},
                    tool_name=tool_name,
                    arguments=arguments,
                )
            elif server_type == "sse":
                return await self._execute_sse(
                    url=config["url"],
                    headers=config["headers"] or {},
                    tool_name=tool_name,
                    arguments=arguments,
                )
            else:
                return {"error": f"Tipo de servidor '{server_type}' no soportado para ejecución."}

        except Exception as e:
            logger.error(
                "Error ejecutando tool '%s' en servidor '%s' para agente '%s': %s",
                tool_name,
                config_id,
                agent_id,
                str(e),
                exc_info=True,
            )
            return {"error": f"Error ejecutando herramienta: {str(e)}"}

    async def _execute_stdio(
        self,
        command: str,
        args: list[str],
        env_vars: dict,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        """Ejecuta un tool en un servidor MCP stdio."""
        import os

        merged_env = {**os.environ, **env_vars}
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=merged_env,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return _parse_mcp_result(result)

    async def _execute_sse(
        self,
        url: str,
        headers: dict,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        """Ejecuta un tool en un servidor MCP SSE."""
        async with sse_client(url=url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return _parse_mcp_result(result)

    async def get_all_tools_for_agent(
        self, agent_id: str
    ) -> list[dict]:
        """
        Retorna todas las herramientas disponibles de todos los servidores
        MCP conectados para un agente, con prefijo de servidor para evitar
        colisiones de nombres.
        """
        async with self._lock:
            agent_sessions = self._sessions.get(agent_id, {})

        all_tools = []
        for config_id, info in agent_sessions.items():
            for tool in info.get("tools", []):
                # Agregar metadata de origen
                enriched_tool = dict(tool)
                enriched_tool["_mcp_server_id"] = config_id
                all_tools.append(enriched_tool)

        return all_tools

    async def disconnect_agent(self, agent_id: str) -> None:
        """Elimina todas las sesiones cacheadas de un agente."""
        async with self._lock:
            self._sessions.pop(agent_id, None)
        logger.info("Sesiones MCP eliminadas para agente '%s'.", agent_id)

    async def disconnect_server(self, agent_id: str, config_id: str) -> None:
        """Elimina la sesión cacheada de un servidor específico."""
        async with self._lock:
            if agent_id in self._sessions:
                self._sessions[agent_id].pop(config_id, None)
        logger.info(
            "Sesión MCP eliminada: servidor '%s', agente '%s'.",
            config_id,
            agent_id,
        )


    async def execute_remote_http(
        self,
        env_config: dict,
        tool_name: str,
        arguments: dict,
        session_token: str | None = None,
        tenant_slug: str | None = None,
        timeout_s: float = 30.0,
    ) -> dict:
        """
        Invoca una MCP_Tool en un servidor MCP remoto HTTP (llamada saliente).

        Resuelve la URL base y el token de servicio a partir de los NOMBRES de
        variables de entorno registrados en `env_config` (`url_env`,
        `service_token_env`) leyendolos desde `Settings`/entorno (nunca del
        codigo). Realiza `POST {URL}/tools/{tool_name}` enviando:
        - `Authorization: Bearer <service_token>` (token de servicio GENIA->MCP)
        - `X-Session-Token: <session_token>` (token de sesion efimero, no persistido)
        - `X-Tenant: <tenant_slug>`

        Args:
            env_config: Dict con `url_env` y `service_token_env` (nombres de env).
            tool_name: Nombre de la MCP_Tool a invocar en el MCP remoto.
            arguments: Parametros de la herramienta.
            session_token: Token de sesion efimero recibido en `metadata`.
            tenant_slug: Slug del tenant (cabecera `X-Tenant`).
            timeout_s: Timeout de la llamada saliente.

        Returns:
            La respuesta JSON del MCP remoto, o `{"error": ...}` ante fallo.
        """
        import os

        import httpx

        from config import settings

        def _resolve(env_name: str | None) -> str | None:
            if not env_name:
                return None
            value = getattr(settings, env_name.lower(), None)
            if value:
                return value
            return os.getenv(env_name)

        url_env = (env_config or {}).get("url_env") or ""
        token_env = (env_config or {}).get("service_token_env") or ""
        base_url = _resolve(url_env)
        service_token = _resolve(token_env)

        if not base_url:
            return {"error": f"URL del MCP remoto no configurada ({url_env})."}
        if not service_token:
            return {
                "error": f"Token de servicio del MCP remoto no configurado ({token_env})."
            }

        headers = {
            "Authorization": f"Bearer {service_token}",
            "Content-Type": "application/json",
        }
        if session_token:
            headers["X-Session-Token"] = session_token
        if tenant_slug:
            headers["X-Tenant"] = tenant_slug

        endpoint = f"{base_url.rstrip('/')}/tools/{tool_name}"
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                response = await client.post(
                    endpoint,
                    json={"params": arguments or {}},
                    headers=headers,
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:  # noqa: BLE001 - se devuelve error controlado
            logger.error(
                "Error invocando MCP remoto '%s': %s", tool_name, str(e)
            )
            return {"error": f"Error invocando MCP remoto: {str(e)}"}

def _parse_mcp_result(result: Any) -> dict:
    """
    Parsea el resultado de una llamada MCP a un diccionario.
    """
    try:
        # El resultado de MCP puede tener .content como lista de ContentBlocks
        if hasattr(result, "content") and isinstance(result.content, list):
            text_parts = []
            for block in result.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif hasattr(block, "data"):
                    text_parts.append(str(block.data))
            return {"result": "\n".join(text_parts)}
        elif hasattr(result, "content"):
            return {"result": str(result.content)}
        else:
            return {"result": str(result)}
    except Exception as e:
        logger.error("Error parseando resultado MCP: %s", str(e))
        return {"result": str(result)}


# ── Instancia global del gestor ──────────────────────────────────────
mcp_client_manager = MCPClientManager()

