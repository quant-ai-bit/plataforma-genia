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
            elif origin == "calendar_builtin":
                # Ejecutar herramienta de Google Calendar
                result = await self._execute_calendar_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    agent_id=agent_id,
                    db=db,
                    agent=agent,
                )
            elif origin == "wasi_builtin":
                # Ejecutar herramienta de inventario inmobiliario Wasi.co
                result = await self._execute_wasi_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    agent=agent,
                )
            elif origin == "database_builtin":
                # Ejecutar consulta en base de datos privada del agente (PreloadedContact)
                result = await self._execute_database_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    agent_id=agent_id,
                    db=db,
                )
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

    async def _execute_calendar_tool(
        self,
        tool_name: str,
        arguments: dict,
        agent_id: str,
        db: Session,
        agent=None,
    ) -> dict:
        """
        Ejecuta una herramienta de Google Calendar.

        Delega al google_calendar_service según el nombre de la tool.
        """
        from services import google_calendar_service

        timezone_str = "America/Bogota"
        if agent and hasattr(agent, "timezone") and agent.timezone:
            timezone_str = agent.timezone

        logger.info(
            "Ejecutando calendar tool '%s' para agente '%s' (tz=%s): %s",
            tool_name,
            agent_id,
            timezone_str,
            json.dumps(arguments, ensure_ascii=False),
        )

        try:
            if tool_name == "check_calendar_availability":
                return await google_calendar_service.check_availability(
                    agent_id=agent_id,
                    db=db,
                    date=arguments["date"],
                    timezone_str=timezone_str,
                )

            elif tool_name == "create_calendar_event":
                date = arguments["date"]
                start_time = arguments["start_time"]
                end_time = arguments["end_time"]
                start_dt = f"{date}T{start_time}:00"
                end_dt = f"{date}T{end_time}:00"

                return await google_calendar_service.create_event(
                    agent_id=agent_id,
                    db=db,
                    summary=arguments["title"],
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    timezone_str=timezone_str,
                    attendee_name=arguments.get("attendee_name", ""),
                    attendee_email=arguments.get("attendee_email", ""),
                    description=arguments.get("description", ""),
                )

            elif tool_name == "list_upcoming_events":
                from datetime import datetime, timedelta
                from zoneinfo import ZoneInfo

                tz = ZoneInfo(timezone_str)
                now = datetime.now(tz)
                days_ahead = arguments.get("days_ahead", 7)
                time_max = (now + timedelta(days=days_ahead)).isoformat()

                return {
                    "events": await google_calendar_service.list_events(
                        agent_id=agent_id,
                        db=db,
                        time_min=now.isoformat(),
                        time_max=time_max,
                        timezone_str=timezone_str,
                    )
                }

            elif tool_name == "cancel_calendar_event":
                return await google_calendar_service.cancel_event(
                    agent_id=agent_id,
                    db=db,
                    event_id=arguments["event_id"],
                    cancellation_reason=arguments.get("cancellation_reason", ""),
                )

            elif tool_name == "reschedule_calendar_event":
                new_date = arguments["new_date"]
                new_start = arguments["new_start_time"]
                new_end = arguments["new_end_time"]
                new_start_dt = f"{new_date}T{new_start}:00"
                new_end_dt = f"{new_date}T{new_end}:00"

                return await google_calendar_service.reschedule_event(
                    agent_id=agent_id,
                    db=db,
                    event_id=arguments["event_id"],
                    new_start=new_start_dt,
                    new_end=new_end_dt,
                    timezone_str=timezone_str,
                )

            else:
                return {"error": f"Herramienta de calendario '{tool_name}' no reconocida."}

        except Exception as e:
            logger.error(
                "Error ejecutando calendar tool '%s': %s",
                tool_name,
                str(e),
                exc_info=True,
            )
            return {"error": f"Error en el calendario: {str(e)}"}

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

    async def _execute_wasi_tool(
        self,
        tool_name: str,
        arguments: dict,
        agent=None,
    ) -> dict[str, Any]:
        """
        Ejecuta herramientas de Wasi.co (search_wasi_properties, register_wasi_lead).
        Manejo DEFENSIVO: si Wasi falla, retorna un mensaje útil sin romper la conversación.
        """
        from services import wasi_service

        if agent is None or not agent.wasi_connected or not agent.wasi_token:
            return {
                "status": "unavailable",
                "message": (
                    "El inventario inmobiliario no está disponible en este momento. "
                    "Por favor consulta directamente con el asesor."
                ),
            }

        try:
            from services.encryption_service import decrypt
            raw_token = decrypt(agent.wasi_token)
        except Exception:
            raw_token = agent.wasi_token  # fallback sin descifrar

        company_id = agent.wasi_company_id or ""

        try:
            if tool_name == "search_wasi_properties":
                results = await wasi_service.search_wasi_properties(
                    company_id=company_id,
                    wasi_token=raw_token,
                    tipo_propiedad=arguments.get("tipo_propiedad"),
                    proposito=arguments.get("proposito"),
                    presupuesto_min=arguments.get("presupuesto_min"),
                    presupuesto_max=arguments.get("presupuesto_max"),
                    zona=arguments.get("zona"),
                    max_results=3,
                )
                if not results:
                    return {
                        "status": "no_results",
                        "message": (
                            "No encontramos propiedades disponibles con esos criterios en este momento. "
                            "Te recomendamos ampliar el presupuesto o la zona de búsqueda, "
                            "o hablar con un asesor para opciones adicionales."
                        ),
                        "properties": [],
                    }
                return {
                    "status": "success",
                    "total": len(results),
                    "properties": results,
                    "message": f"Encontré {len(results)} propiedad(es) que se ajustan a tu búsqueda.",
                }

            elif tool_name == "register_wasi_lead":
                success = await wasi_service.create_wasi_lead(
                    company_id=company_id,
                    wasi_token=raw_token,
                    lead_data=arguments,
                )
                return {
                    "status": "registered" if success else "failed",
                    "message": (
                        "Tus datos han sido registrados exitosamente. Un asesor se pondrá en contacto contigo pronto."
                        if success else
                        "No pudimos registrar tus datos en este momento, pero el asesor tiene toda tu información."
                    ),
                }
            else:
                return {"error": f"Herramienta Wasi desconocida: {tool_name}"}

        except Exception as e:
            logger.error("_execute_wasi_tool '%s' error: %s", tool_name, e, exc_info=True)
            return {
                "status": "error",
                "message": (
                    "Hubo un problema temporal al consultar el inventario. "
                    "Un asesor te ayudará con opciones personalizadas."
                ),
            }

    async def _execute_database_tool(
        self,
        tool_name: str,
        arguments: dict,
        agent_id: str,
        db: Session = None,
    ) -> dict:
        """
        Ejecuta búsquedas en la base de datos privada precargada del agente (PreloadedContact).
        Permite que el agente busque por nombre, teléfono, email, cédula, inmueble, canon o cualquier
        campo guardado en custom_data.
        """
        close_session = False
        if not db:
            from database import SessionLocal
            db = SessionLocal()
            close_session = True

        try:
            from models.contact import PreloadedContact
            import re

            query_raw = str(arguments.get("query", "")).strip()
            if not query_raw:
                return {
                    "status": "no_query",
                    "encontrados": 0,
                    "resultados": [],
                    "mensaje": "No se proporcionó término de búsqueda.",
                }

            query_lower = query_raw.lower()
            clean_digits = re.sub(r"\D", "", query_raw)

            # Consultar contactos del agente
            contacts = (
                db.query(PreloadedContact)
                .filter(PreloadedContact.agent_id == agent_id)
                .all()
            )

            if not contacts:
                return {
                    "status": "empty_database",
                    "encontrados": 0,
                    "resultados": [],
                    "mensaje": "La base de datos de este agente no tiene registros cargados aún.",
                }

            matched = []
            for c in contacts:
                is_match = False
                # 1. Teléfono o números
                if clean_digits and len(clean_digits) >= 4 and clean_digits in (c.phone or ""):
                    is_match = True
                # 2. Nombre
                elif query_lower in (c.name or "").lower():
                    is_match = True
                # 3. Email
                elif query_lower in (c.email or "").lower():
                    is_match = True
                # 4. Notas
                elif query_lower in (c.notes or "").lower():
                    is_match = True
                # 5. custom_data (cédula, apartamento, canon, propietario, etc.)
                elif c.custom_data and isinstance(c.custom_data, dict):
                    for k, v in c.custom_data.items():
                        if query_lower in str(k).lower() or query_lower in str(v).lower():
                            is_match = True
                            break

                if is_match:
                    item = {
                        "nombre": c.name,
                        "telefono": c.phone,
                        "email": c.email or "No registrado",
                        "notas": c.notes or "",
                    }
                    if c.custom_data and isinstance(c.custom_data, dict):
                        item["datos_adicionales"] = c.custom_data
                    matched.append(item)
                    if len(matched) >= 5:  # Máximo 5 registros
                        break

            if not matched:
                return {
                    "status": "not_found",
                    "encontrados": 0,
                    "resultados": [],
                    "mensaje": f"No se encontró ningún registro en la base de datos que coincida con '{query_raw}'.",
                }

            return {
                "status": "success",
                "encontrados": len(matched),
                "resultados": matched,
                "mensaje": f"Se encontraron {len(matched)} registro(s) coincidente(s) en la base de datos.",
            }

        except Exception as e:
            logger.error("_execute_database_tool '%s' error para agente %s: %s", tool_name, agent_id, e, exc_info=True)
            return {
                "status": "error",
                "message": f"Error defensivo consultando base de datos: {str(e)}",
            }
        finally:
            if close_session and db:
                db.close()


# ── Instancia global del registro ────────────────────────────────────
mcp_registry = MCPToolRegistry()



