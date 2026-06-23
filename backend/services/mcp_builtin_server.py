"""
Servidor MCP built-in para PLATAFORMA GENIA.

Registra las herramientas nativas de la plataforma (save_lead, handoff,
alert, RAG) como tools MCP estándar que pueden ser descubiertos y
ejecutados por el sistema de chat.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Definiciones de herramientas MCP built-in ────────────────────────

def get_builtin_tools(custom_fields: list[dict] | None = None) -> list[dict]:
    """
    Retorna la lista de herramientas built-in en formato MCP.

    Las herramientas dinámicas (como save_lead_info) se construyen
    a partir de los custom_fields del agente.

    Args:
        custom_fields: Campos personalizados del agente para la captura de leads.

    Returns:
        Lista de tools en formato MCP.
    """
    custom_fields = custom_fields or []

    # ── save_lead_info (dinámico según campos del agente) ──
    lead_properties: dict = {
        "name": {
            "type": "string",
            "description": "El nombre del cliente potencial (lead).",
        }
    }
    required_fields: list[str] = ["name"]

    for field in custom_fields:
        field_name: str = field.get("key") or field.get("name") or ""
        if not field_name or field_name == "name":
            continue

        field_type: str = field.get("type", "string")
        field_desc: str = field.get(
            "description", f"Campo personalizado: {field_name}"
        )

        lead_properties[field_name] = {
            "type": field_type,
            "description": field_desc,
        }

    tools = [
        {
            "name": "save_lead_info",
            "description": (
                "Guarda o actualiza la información del cliente potencial (lead) "
                "en la base de datos cuando se detectan sus datos durante la conversación."
            ),
            "inputSchema": {
                "type": "object",
                "properties": lead_properties,
                "required": required_fields,
            },
        },
        {
            "name": "trigger_human_handoff",
            "description": (
                "Transfiere la conversación a un operador humano cuando el cliente "
                "lo solicita, cuando está interesado en planes de oficinas privadas "
                "por meses (planes mensuales), o cuando realiza una consulta muy "
                "compleja que excede tu base de conocimiento."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "alert_owner_about_unanswered_query",
            "description": (
                "Alerta al administrador/dueño sobre una consulta del cliente que "
                "no puedes responder porque no tienes la información necesaria en "
                "tu base de conocimiento."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "unanswered_question": {
                        "type": "string",
                        "description": "La pregunta exacta del usuario que no se pudo responder.",
                    }
                },
                "required": ["unanswered_question"],
            },
        },
    ]

    return tools


async def execute_builtin_tool(
    tool_name: str, arguments: dict
) -> dict[str, Any]:
    """
    Ejecuta una herramienta built-in y retorna el resultado.

    Las herramientas built-in no realizan la acción real directamente
    (eso lo hace el pipeline de chat), sino que retornan el resultado
    esperado para que el LLM pueda continuar la conversación.

    Args:
        tool_name: Nombre de la herramienta a ejecutar.
        arguments: Argumentos de la herramienta.

    Returns:
        Diccionario con el resultado de la ejecución.
    """
    if tool_name == "save_lead_info":
        logger.info("MCP Built-in: Ejecutando save_lead_info con args: %s", arguments)
        return {"result": "Información guardada exitosamente."}

    elif tool_name == "trigger_human_handoff":
        logger.info("MCP Built-in: Ejecutando trigger_human_handoff.")
        return {"result": "Conversación derivada a humano exitosamente."}

    elif tool_name == "alert_owner_about_unanswered_query":
        question = arguments.get("unanswered_question", "")
        logger.info(
            "MCP Built-in: Alerta de pregunta sin respuesta: %s", question
        )
        return {"result": "Pregunta guardada y alerta emitida al administrador."}

    else:
        logger.warning("MCP Built-in: Herramienta '%s' no reconocida.", tool_name)
        return {"error": f"Herramienta '{tool_name}' no encontrada en el servidor built-in."}


# ── Verificación de si un tool es built-in ───────────────────────────

BUILTIN_TOOL_NAMES = {
    "save_lead_info",
    "trigger_human_handoff",
    "alert_owner_about_unanswered_query",
}


def is_builtin_tool(tool_name: str) -> bool:
    """Verifica si un nombre de herramienta corresponde a un tool built-in."""
    return tool_name in BUILTIN_TOOL_NAMES
