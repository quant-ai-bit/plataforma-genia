"""
Servicio de IA para PLATAFORMA GENIA.

Gestiona la comunicación con proveedores LLM (Groq) para generar
respuestas conversacionales con soporte de function-calling para
captura automática de datos de leads.
"""

import asyncio
import json
import logging
import re
import httpx

from groq import AsyncGroq

from config import settings

logger = logging.getLogger(__name__)

# ── Cliente Groq (inicialización global) ─────────────────────────────
groq_client = AsyncGroq(api_key=settings.groq_api_key)


# ── Estructura Auxiliar y Configuración de OpenRouter ────────────────
class Struct:
    """Clase auxiliar para acceder a claves de diccionario como atributos."""
    def __init__(self, **entries):
        for k, v in entries.items():
            if isinstance(v, dict):
                self.__dict__[k] = Struct(**v)
            elif isinstance(v, list):
                self.__dict__[k] = [Struct(**item) if isinstance(item, dict) else item for item in v]
            else:
                self.__dict__[k] = v

# Mapa de precios por millón de tokens (input/output) en USD
PRICING_MAP = {
    # Groq Models
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama3-70b-8192": {"input": 0.59, "output": 0.79},
    "llama3-8b-8192": {"input": 0.05, "output": 0.08},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    "gemma2-9b-it": {"input": 0.20, "output": 0.20},
    
    # Gemini Models (directo o via OpenRouter)
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    
    # OpenRouter Models
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
    "anthropic/claude-3.5-sonnet:beta": {"input": 3.00, "output": 15.00},
    "google/gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "openai/gpt-4o-mini": {"input": 0.150, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
}

def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calcula el costo total en USD a partir de la cantidad de tokens."""
    prices = PRICING_MAP.get(model, {"input": 0.5, "output": 1.5})
    input_cost = (prompt_tokens / 1_000_000.0) * prices["input"]
    output_cost = (completion_tokens / 1_000_000.0) * prices["output"]
    return input_cost + output_cost

def message_to_dict(message) -> dict:
    """Convierte un mensaje (objeto del SDK de Groq o dict) a un diccionario estándar."""
    if isinstance(message, dict):
        return message
    
    d = {"role": message.role, "content": message.content}
    if hasattr(message, "tool_calls") and message.tool_calls:
        d["tool_calls"] = []
        for tc in message.tool_calls:
            d["tool_calls"].append({
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            })
    return d


# ── Construcción dinámica de herramientas (tools) ────────────────────

def build_lead_tools(custom_fields: list[dict]) -> list[dict]:
    """
    Genera la definición de herramientas (function-calling) para ``save_lead_info``,
    ``trigger_human_handoff`` y ``alert_owner_about_unanswered_query``
    a partir de los campos personalizados del agente.

    El campo ``name`` (nombre del lead) se incluye siempre como obligatorio para save_lead_info.
    """
    # Propiedades dinámicas construidas a partir de custom_fields
    properties: dict = {
        "name": {
            "type": "string",
            "description": "El nombre del cliente potencial (lead).",
        }
    }
    required_fields: list[str] = ["name"]

    for field in custom_fields:
        field_name: str = field.get("key") or field.get("name") or ""
        if not field_name or field_name == "name":
            # Evitar duplicar el campo 'name' o procesar campos sin nombre
            continue

        field_type: str = field.get("type", "string")
        field_desc: str = field.get("description", f"Campo personalizado: {field_name}")

        properties[field_name] = {
            "type": field_type,
            "description": field_desc,
        }

        # Los campos personalizados se marcan como opcionales en el esquema JSON de la herramienta
        # para permitir que el LLM llame a save_lead_info de forma incremental/parcial.
        # if field.get("required", False):
        #     required_fields.append(field_name)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "save_lead_info",
                "description": (
                    "Guarda o actualiza la información del cliente potencial (lead) "
                    "en la base de datos cuando se detectan sus datos durante la conversación."
                ),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_fields,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "trigger_human_handoff",
                "description": (
                    "Transfiere la conversación a un operador humano cuando el cliente lo solicita, "
                    "cuando está interesado en planes de oficinas privadas por meses (planes mensuales), "
                    "o cuando realiza una consulta muy compleja que excede tu base de conocimiento."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "alert_owner_about_unanswered_query",
                "description": (
                    "Alerta al administrador/dueño sobre una consulta del cliente que no puedes responder "
                    "porque no tienes la información necesaria en tu base de conocimiento."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "unanswered_question": {
                            "type": "string",
                            "description": "La pregunta exacta del usuario que no se pudo responder."
                        }
                    },
                    "required": ["unanswered_question"]
                }
            }
        }
    ]

    return tools


async def post_openrouter_with_retries(client: httpx.AsyncClient, payload: dict, max_retries: int = 3) -> httpx.Response:
    """Realiza una petición POST a OpenRouter con reintentos para errores transitorios."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://genia.plataforma",
        "X-Title": "Plataforma Genia",
        "Content-Type": "application/json",
    }
    
    last_exc = None
    for attempt in range(max_retries):
        try:
            logger.info("Enviando petición a OpenRouter (Intento %s/%s)...", attempt + 1, max_retries)
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            # Si el código es 429 (rate limit) o 5xx (servidor saturado), reintentamos
            if response.status_code == 429 or response.status_code >= 500:
                logger.warning(
                    "OpenRouter retornó código %s en intento %s. Reintentando...",
                    response.status_code,
                    attempt + 1
                )
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial (1s, 2s, 4s...)
                continue
            return response
        except (httpx.HTTPError, httpx.StreamError) as exc:
            last_exc = exc
            logger.warning(
                "Error de red/conexión con OpenRouter en intento %s: %s. Reintentando...",
                attempt + 1,
                str(exc)
            )
            await asyncio.sleep(2 ** attempt)
            
    if last_exc:
        raise last_exc
    raise Exception("Límite de reintentos alcanzado para OpenRouter sin una respuesta exitosa.")


async def chat_with_agent(
    agent_model_data: dict,
    conversation_history: list[dict],
    user_message: str,
    knowledge_context: str = "",
    db=None,
    agent_id: str = "",
) -> tuple[str, dict | None, bool, str | None, int, int]:
    """
    Envía un mensaje al LLM configurado para el agente y devuelve la
    respuesta junto con los datos de lead capturados, si se activó el handoff
    o si hubo una pregunta sin respuesta, y el conteo de tokens de prompt y completion.

    Args:
        agent_model_data: diccionario con la configuración del agente:
            - ``provider`` (str): proveedor LLM (``"groq"`` / ``"openrouter"`` / ``"gemini"``).
            - ``model`` (str): nombre del modelo a usar.
            - ``system_prompt`` (str): prompt de sistema personalizado.
            - ``temperature`` (float): creatividad del modelo.
            - ``max_tokens`` (int): máximo de tokens de respuesta.
            - ``custom_fields`` (list[dict]): campos personalizados del agente.
        conversation_history: historial de mensajes previos
            (``[{"role": "user"|"assistant", "content": "..."}]``).
        user_message: mensaje actual del usuario.
        knowledge_context: contexto de base de conocimiento (RAG) opcional.
        db: sesión de base de datos (opcional, para cargar MCP tools externos).
        agent_id: ID del agente (opcional, para cargar MCP tools externos).

    Returns:
        Tupla ``(respuesta_texto, datos_lead_o_none, handoff_activado, pregunta_sin_respuesta_o_none, prompt_tokens, completion_tokens)``.
    """
    provider: str = agent_model_data.get("provider", "groq")
    model_name: str = agent_model_data.get("model", "llama-3.3-70b-versatile")
    system_prompt: str = agent_model_data.get("system_prompt", "")
    temperature: float = agent_model_data.get("temperature", 0.7)
    max_tokens: int = agent_model_data.get("max_tokens", 1024)
    custom_fields: list[dict] = agent_model_data.get("custom_fields", [])

    # ── Construir prompt de sistema con contexto de conocimiento ──
    full_system_prompt = system_prompt
    if knowledge_context:
        full_system_prompt += (
            "\n\n[CONTEXTO DE NEGOCIO - Usa esta información para responder:]\n"
            f"{knowledge_context}"
        )

    # ── Armar arreglo de mensajes ─────────────────────────────────
    messages: list[dict] = [{"role": "system", "content": full_system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # ── Herramientas: MCP Registry (built-in + externas) ─────────
    from services.mcp_registry import mcp_registry

    try:
        tools, tool_origin_map = await mcp_registry.get_tools_for_agent(
            db=db, agent_id=agent_id, custom_fields=custom_fields
        )
    except Exception as e:
        logger.warning("Error cargando MCP tools, usando fallback built-in: %s", str(e))
        tools = build_lead_tools(custom_fields)
        tool_origin_map = {
            "save_lead_info": "builtin",
            "trigger_human_handoff": "builtin",
            "alert_owner_about_unanswered_query": "builtin",
        }

    # ── Variables de resultado ────────────────────────────────────
    final_text: str = ""
    lead_data: dict | None = None
    handoff_triggered: bool = False
    unanswered_question: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0

    try:
        # ── Determinar cliente según proveedor y realizar llamada ──
        if provider == "groq":
            response = await groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            if response.usage:
                prompt_tokens += response.usage.prompt_tokens
                completion_tokens += response.usage.completion_tokens

        elif provider == "openrouter":
            clean_messages = [message_to_dict(m) for m in messages]
            payload = {
                "model": model_name,
                "messages": clean_messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient() as client:
                response = await post_openrouter_with_retries(client, payload)
                if response.status_code != 200:
                    raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
                
                resp_json = response.json()
                choice = resp_json["choices"][0]
                response_message = choice["message"]
                
                raw_tool_calls = response_message.get("tool_calls")
                if raw_tool_calls:
                    tool_calls = [Struct(**tc) for tc in raw_tool_calls]
                else:
                    tool_calls = None
                
                usage_data = resp_json.get("usage", {})
                prompt_tokens += usage_data.get("prompt_tokens", 0)
                completion_tokens += usage_data.get("completion_tokens", 0)
        else:
            logger.warning("Proveedor '%s' no soportado aún.", provider)
            return (
                "⚠️ El proveedor de IA configurado no está soportado actualmente.",
                None,
                False,
                None,
                0,
                0,
            )

        if tool_calls:
            # Agregar la respuesta del asistente con la tool-call al historial
            messages.append(response_message)

            for tool_call in tool_calls:
                func_name = tool_call.function.name
                args: dict = json.loads(tool_call.function.arguments)

                # ── Ejecutar via MCP Registry ────────────────────
                result = await mcp_registry.execute_tool(
                    tool_name=func_name,
                    arguments=args,
                    tool_origin_map=tool_origin_map,
                    agent_id=agent_id,
                )

                # ── Procesar resultado según tipo de tool ────────
                if func_name == "save_lead_info":
                    lead_data = args
                    logger.info(
                        "Datos de lead capturados por function-calling: %s", args
                    )
                elif func_name == "trigger_human_handoff":
                    handoff_triggered = True
                    logger.info("Human handoff triggered by the agent.")
                elif func_name == "alert_owner_about_unanswered_query":
                    unanswered_question = args.get("unanswered_question", user_message)
                    logger.info(
                        "Alerta de pregunta sin respuesta registrada: %s", unanswered_question
                    )

                # Agregar resultado de la herramienta al historial
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": json.dumps(result),
                    }
                )

            # ── Segunda llamada (sin tools) para texto final ──
            if provider == "groq":
                second_response = await groq_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                final_text = second_response.choices[0].message.content or ""
                if second_response.usage:
                    prompt_tokens += second_response.usage.prompt_tokens
                    completion_tokens += second_response.usage.completion_tokens
            elif provider == "openrouter":
                clean_messages = [message_to_dict(m) for m in messages]
                payload = {
                    "model": model_name,
                    "messages": clean_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                async with httpx.AsyncClient() as client:
                    second_response = await post_openrouter_with_retries(client, payload)
                    if second_response.status_code != 200:
                        raise Exception(f"OpenRouter API error: {second_response.status_code} - {second_response.text}")
                    
                    second_resp_json = second_response.json()
                    final_text = second_resp_json["choices"][0]["message"]["content"] or ""
                    
                    second_usage_data = second_resp_json.get("usage", {})
                    prompt_tokens += second_usage_data.get("prompt_tokens", 0)
                    completion_tokens += second_usage_data.get("completion_tokens", 0)
        else:
            if provider == "openrouter":
                final_text = response_message.get("content") or ""
            else:
                final_text = response_message.content or ""

        # Limpiar posibles fugas de texto de function-calling (como <function=...>)
        if final_text:
            final_text = re.sub(r"<function=\w+>.*?</function>", "", final_text, flags=re.DOTALL)
            final_text = re.sub(r"<function=\w+>.*$", "", final_text, flags=re.DOTALL)
            final_text = final_text.strip()

    except Exception as exc:
        error_str = str(exc)
        logger.error("Error en chat_with_agent: %s", error_str, exc_info=True)

        if any(kw in error_str for kw in ("Quota exceeded", "429", "rate_limit")):
            final_text = (
                "⚠️ Se ha superado el límite de cuota (Rate Limit) de la API. "
                "Por favor, espera unos segundos e inténtalo de nuevo."
            )
        elif any(
            kw in error_str.lower() for kw in ("api key", "unauthorized", "401")
        ):
            final_text = (
                "⚠️ Error de autenticación: La clave API del proveedor de IA "
                "no está configurada o es inválida."
            )
        else:
            final_text = (
                "⚠️ Hubo un error procesando tu solicitud con el servicio de IA. "
                "Por favor, inténtalo de nuevo más tarde."
            )

    return final_text, lead_data, handoff_triggered, unanswered_question, prompt_tokens, completion_tokens


# ── Modelos disponibles por proveedor ────────────────────────────────

def get_available_models(provider: str) -> list[str]:
    """
    Retorna la lista de modelos disponibles para un proveedor dado.

    Args:
        provider: identificador del proveedor (``"groq"``, ``"openrouter"`` o ``"gemini"``).

    Returns:
        Lista de nombres de modelo disponibles.
    """
    if provider == "groq":
        return settings.available_groq_models
    elif provider == "gemini":
        return settings.available_gemini_models
    elif provider == "openrouter":
        return settings.available_openrouter_models
    else:
        return []


# ── Delegacion en Model_Service (genia-agent-platform, Tarea 2.4) ─────
# Nueva ruta de generacion multi-proveedor con timeout/retry/fallback.
# Se mantiene `chat_with_agent` intacto por compatibilidad; este helper es la
# via recomendada para la API publica `/v1`, que delega en `ModelService`.

async def generate_via_model_service(
    messages: list[dict],
    system_prompt: str | None = None,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    usage_ctx=None,
):
    """
    Genera una respuesta delegando en `ModelService` (Vertex -> Groq -> OpenRouter).

    Construye un `GenerationRequest` y orquesta los proveedores en el orden
    configurado (`MODEL_FALLBACK_ORDER`) aplicando timeout/retry/fallback. Si se
    provee `usage_ctx`, registra el consumo en el Usage_Record.

    Args:
        messages: Historial de mensajes en formato chat.
        system_prompt: Prompt de sistema opcional.
        tools: Esquemas de MCP_Tool (function-calling), opcional.
        max_tokens: Maximo de tokens de respuesta.
        temperature: Temperatura de generacion.
        usage_ctx: Contexto opcional para registrar el consumo (Usage_Record).

    Returns:
        `GenerationResult` del proveedor que respondio con exito.

    Raises:
        ModelUnavailableError: Si todos los proveedores fallan (mapeable a 503).
    """
    # Imports diferidos para evitar ciclos de import en tiempo de carga.
    from services.model_service import ModelService
    from services.providers.base import GenerationRequest

    req = GenerationRequest(
        messages=messages,
        system_prompt=system_prompt,
        tools=tools,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    service = ModelService.from_settings()
    return await service.generate(req, usage_ctx=usage_ctx)
