"""
Adaptador MCP agnóstico de modelo para PLATAFORMA GENIA.

Traduce MCP Tools al formato de function-calling nativo de cada proveedor
(Groq, OpenRouter, Gemini), permitiendo que los tools MCP funcionen con
cualquier LLM sin depender de un proveedor específico.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def mcp_tools_to_function_calling(mcp_tools: list[dict]) -> list[dict]:
    """
    Convierte una lista de tools en formato MCP al formato estándar
    de function-calling (compatible con OpenAI/Groq/OpenRouter).

    El formato MCP es:
        {
            "name": "tool_name",
            "description": "...",
            "inputSchema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }

    El formato OpenAI/Groq/OpenRouter es:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }

    Args:
        mcp_tools: Lista de herramientas en formato MCP.

    Returns:
        Lista de herramientas en formato function-calling estándar.
    """
    fc_tools = []
    for tool in mcp_tools:
        # Extraer el input schema, limpiando claves internas de MCP
        input_schema = tool.get("inputSchema", {})
        parameters = _clean_json_schema(input_schema)

        fc_tool = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": parameters,
            },
        }
        fc_tools.append(fc_tool)

    return fc_tools


def function_call_to_mcp_request(
    tool_name: str, arguments_str: str
) -> tuple[str, dict]:
    """
    Convierte una llamada de function-calling del LLM a una solicitud MCP.

    Args:
        tool_name: Nombre de la herramienta invocada.
        arguments_str: Argumentos en formato JSON string.

    Returns:
        Tupla (nombre_herramienta, argumentos_dict).
    """
    try:
        arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
    except json.JSONDecodeError:
        logger.error("Error al parsear argumentos de function-call: %s", arguments_str)
        arguments = {}

    return tool_name, arguments


def mcp_result_to_tool_response(
    tool_call_id: str, tool_name: str, result: Any
) -> dict:
    """
    Convierte el resultado de una ejecución MCP al formato de respuesta
    de herramienta para el historial del chat (compatible con todos los
    proveedores).

    Args:
        tool_call_id: ID de la llamada de herramienta original.
        tool_name: Nombre de la herramienta ejecutada.
        result: Resultado devuelto por el servidor MCP.

    Returns:
        Diccionario de mensaje con rol 'tool'.
    """
    # Serializar el resultado a string si no lo es
    if isinstance(result, dict) or isinstance(result, list):
        content = json.dumps(result, ensure_ascii=False)
    elif isinstance(result, str):
        content = result
    else:
        content = str(result)

    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": content,
    }


def _clean_json_schema(schema: dict) -> dict:
    """
    Limpia un JSON Schema removiendo claves específicas de MCP que
    no son compatibles con el formato de function-calling.
    """
    # Copiar para no mutar el original
    cleaned = dict(schema)

    # Remover claves no estándar
    for key in ("$schema", "$id", "additionalProperties"):
        cleaned.pop(key, None)

    # Asegurar que 'type' y 'properties' existan con valores por defecto
    if "type" not in cleaned:
        cleaned["type"] = "object"
    if "properties" not in cleaned:
        cleaned["properties"] = {}

    return cleaned
