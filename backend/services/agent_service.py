"""
agent_service: gestion del Agent_Config por tenant para PLATAFORMA GENIA.

Reutiliza la entidad `Agent` existente (que ya posee `tenant_id`,
`system_prompt` y `enabled_mcp_tools`) y expone operaciones de lectura/escritura
acotadas SIEMPRE al `tenant_id`, de modo que actualizar la configuracion de un
tenant nunca afecta a otros.

Funciones principales:
- `get_for_tenant`: recupera el Agent_Config (primario) de un tenant.
- `get_system_prompt` / `set_system_prompt`: round-trip del prompt de sistema.
- `get_enabled_tools` / `set_enabled_tools` / `enable_tool` / `disable_tool`:
  gestion del catalogo de MCP_Tools habilitadas del tenant.

Feature: genia-agent-platform (Tarea 6.1)
"""

import logging

from sqlalchemy.orm import Session

from models.agent import Agent

logger = logging.getLogger(__name__)


def get_for_tenant(db: Session, tenant_id: str) -> Agent | None:
    """
    Recupera el Agent_Config primario asociado a un tenant.

    Args:
        db: Sesion de base de datos.
        tenant_id: Identificador del tenant.

    Returns:
        El `Agent` mas reciente del tenant, o `None` si no tiene ninguno.
    """
    if not tenant_id:
        return None
    return (
        db.query(Agent)
        .filter(Agent.tenant_id == tenant_id)
        .order_by(Agent.created_at.asc())
        .first()
    )


def get_system_prompt(db: Session, tenant_id: str) -> str | None:
    """Devuelve el `system_prompt` del Agent_Config del tenant, o None."""
    agent = get_for_tenant(db, tenant_id)
    return agent.system_prompt if agent else None


def set_system_prompt(db: Session, tenant_id: str, system_prompt: str) -> Agent | None:
    """
    Actualiza el `system_prompt` del Agent_Config del tenant (round-trip 3.1).

    La escritura esta acotada por `tenant_id`, por lo que no afecta a otros
    tenants. Devuelve el agente actualizado o `None` si el tenant no tiene uno.
    """
    agent = get_for_tenant(db, tenant_id)
    if agent is None:
        return None
    agent.system_prompt = system_prompt
    db.flush()
    logger.info("system_prompt actualizado para tenant %s", tenant_id)
    return agent


def get_enabled_tools(db: Session, tenant_id: str) -> list[str]:
    """Devuelve la lista de MCP_Tools habilitadas del Agent_Config del tenant."""
    agent = get_for_tenant(db, tenant_id)
    if agent is None:
        return []
    return list(agent.enabled_mcp_tools or [])


def set_enabled_tools(db: Session, tenant_id: str, tools: list[str]) -> Agent | None:
    """
    Reemplaza el conjunto de MCP_Tools habilitadas del tenant.

    Normaliza el conjunto (sin duplicados, preservando orden de aparicion) y lo
    persiste acotado por `tenant_id`. No afecta el Agent_Config de otros tenants.
    """
    agent = get_for_tenant(db, tenant_id)
    if agent is None:
        return None
    seen: set[str] = set()
    normalized: list[str] = []
    for name in tools or []:
        if name and name not in seen:
            seen.add(name)
            normalized.append(name)
    agent.enabled_mcp_tools = normalized
    db.flush()
    logger.info("enabled_mcp_tools actualizado para tenant %s (%d tools)", tenant_id, len(normalized))
    return agent


def enable_tool(db: Session, tenant_id: str, tool_name: str) -> Agent | None:
    """Habilita una MCP_Tool en el Agent_Config del tenant (idempotente)."""
    current = get_enabled_tools(db, tenant_id)
    if tool_name and tool_name not in current:
        current.append(tool_name)
    return set_enabled_tools(db, tenant_id, current)


def disable_tool(db: Session, tenant_id: str, tool_name: str) -> Agent | None:
    """Deshabilita una MCP_Tool en el Agent_Config del tenant (idempotente)."""
    current = [t for t in get_enabled_tools(db, tenant_id) if t != tool_name]
    return set_enabled_tools(db, tenant_id, current)


def is_tool_enabled(db: Session, tenant_id: str, tool_name: str) -> bool:
    """Indica si una MCP_Tool esta habilitada para el tenant."""
    return tool_name in get_enabled_tools(db, tenant_id)


def upsert(
    db: Session,
    tenant_id: str,
    system_prompt: str,
    model: str,
    model_params: dict | None = None,
    enabled_mcp_tools: list[str] | None = None,
    provider: str = "vertex",
    name: str | None = None,
) -> Agent:
    """
    Crea o actualiza (idempotente) el Agent_Config primario de un tenant.

    Reutiliza la entidad `Agent` ya asociada al tenant si existe (acotado por
    `tenant_id`); de lo contrario crea uno nuevo. Aplica `system_prompt`,
    `model`/`provider`, los parametros de generacion (`temperature`,
    `max_tokens` desde `model_params`) y el catalogo de `enabled_mcp_tools`.
    Re-ejecutar no duplica el agente del tenant.

    Args:
        db: Sesion de base de datos.
        tenant_id: Identificador del tenant propietario.
        system_prompt: Prompt de sistema del Copilot_Agent.
        model: Modelo de LLM (ej: VERTEX_GEMINI_MODEL).
        model_params: Parametros de generacion (temperature, max_tokens).
        enabled_mcp_tools: Catalogo de MCP_Tools habilitadas del tenant.
        provider: Proveedor del modelo (por defecto 'vertex').
        name: Nombre visible del agente (opcional).

    Returns:
        El `Agent` (Agent_Config) creado o actualizado.
    """
    params = model_params or {}
    temperature = params.get("temperature")
    max_tokens = params.get("max_tokens")

    seen: set[str] = set()
    normalized_tools: list[str] = []
    for tool_name in enabled_mcp_tools or []:
        if tool_name and tool_name not in seen:
            seen.add(tool_name)
            normalized_tools.append(tool_name)

    agent = get_for_tenant(db, tenant_id)
    if agent is None:
        agent = Agent(
            tenant_id=tenant_id,
            name=name or "Copilot",
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            enabled_mcp_tools=normalized_tools,
        )
        if temperature is not None:
            agent.temperature = float(temperature)
        if max_tokens is not None:
            agent.max_tokens = int(max_tokens)
        db.add(agent)
        db.flush()
        logger.info("Agent_Config creado para tenant %s (model=%s)", tenant_id, model)
        return agent

    agent.system_prompt = system_prompt
    agent.provider = provider
    agent.model = model
    agent.enabled_mcp_tools = normalized_tools
    if name:
        agent.name = name
    if temperature is not None:
        agent.temperature = float(temperature)
    if max_tokens is not None:
        agent.max_tokens = int(max_tokens)
    db.flush()
    logger.info("Agent_Config actualizado para tenant %s (model=%s)", tenant_id, model)
    return agent
