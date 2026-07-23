"""
Servicio de IA para PLATAFORMA GENIA.

Gestiona la comunicación con Vertex AI (Google Cloud) para generar
respuestas conversacionales con soporte de function-calling para
captura automática de datos de leads.
"""

import asyncio
import json
import logging
import re

from config import settings

logger = logging.getLogger(__name__)


# Mapa de precios por millón de tokens (input/output) en USD — modelos Gemini/Vertex
PRICING_MAP = {
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calcula el costo total en USD a partir de la cantidad de tokens."""
    prices = PRICING_MAP.get(model, {"input": 0.5, "output": 1.5})
    input_cost = (prompt_tokens / 1_000_000.0) * prices["input"]
    output_cost = (completion_tokens / 1_000_000.0) * prices["output"]
    return input_cost + output_cost


def message_to_dict(message) -> dict:
    """Convierte un mensaje (dict u objeto) a un diccionario estándar."""
    if isinstance(message, dict):
        return message
    return {"role": message.role, "content": message.content}


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

        # Forzar 'string' para evitar errores de validación de tipo en los LLM (como Groq 400 validation failed)
        field_type: str = "string"
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
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
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
                            "description": "La pregunta exacta del usuario que no se pudo responder.",
                        }
                    },
                    "required": ["unanswered_question"],
                },
            },
        },
    ]

    return tools


def build_calendar_tools() -> list[dict]:
    """
    Genera las herramientas de function-calling para Google Calendar.

    Incluye: check_calendar_availability, create_calendar_event,
    list_upcoming_events, cancel_calendar_event, reschedule_calendar_event.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "check_calendar_availability",
                "description": (
                    "Verifica la disponibilidad del calendario para una fecha determinada. "
                    "Retorna las franjas horarias disponibles dentro del horario laboral."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Fecha a consultar en formato YYYY-MM-DD (ej: 2026-07-03)",
                        }
                    },
                    "required": ["date"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_calendar_event",
                "description": (
                    "Crea una cita o evento en el calendario del negocio. "
                    "Usa esta herramienta cuando el cliente quiera agendar una cita, "
                    "reunión o reserva."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Título o resumen de la cita (ej: 'Cita con Mar\u00eda - Consulta')",
                        },
                        "date": {
                            "type": "string",
                            "description": "Fecha de la cita en formato YYYY-MM-DD",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Hora de inicio en formato HH:MM (24h, ej: '14:30')",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "Hora de fin en formato HH:MM (24h, ej: '15:30')",
                        },
                        "attendee_name": {
                            "type": "string",
                            "description": "Nombre del cliente o asistente",
                        },
                        "attendee_email": {
                            "type": "string",
                            "description": "Email del cliente (opcional, para enviarle invitación)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Descripción o notas adicionales de la cita",
                        },
                    },
                    "required": ["title", "date", "start_time", "end_time"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_upcoming_events",
                "description": (
                    "Lista los próximos eventos o citas del calendario. "
                    "Útil para informar al cliente sobre las citas programadas."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Número de días hacia adelante para buscar eventos (default: 7)",
                        }
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_calendar_event",
                "description": (
                    "Cancela una cita o evento del calendario. "
                    "IMPORTANTE: Siempre pregunta al cliente el motivo de la cancelación "
                    "antes de usar esta herramienta."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "ID del evento a cancelar (obtenido de list_upcoming_events)",
                        },
                        "cancellation_reason": {
                            "type": "string",
                            "description": "Motivo de la cancelación proporcionado por el cliente",
                        },
                    },
                    "required": ["event_id", "cancellation_reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "reschedule_calendar_event",
                "description": (
                    "Reprograma una cita existente a una nueva fecha y hora. "
                    "Usa esta herramienta cuando el cliente necesite cambiar la fecha u hora de su cita."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "ID del evento a reprogramar",
                        },
                        "new_date": {
                            "type": "string",
                            "description": "Nueva fecha en formato YYYY-MM-DD",
                        },
                        "new_start_time": {
                            "type": "string",
                            "description": "Nueva hora de inicio en formato HH:MM",
                        },
                        "new_end_time": {
                            "type": "string",
                            "description": "Nueva hora de fin en formato HH:MM",
                        },
                    },
                    "required": [
                        "event_id",
                        "new_date",
                        "new_start_time",
                        "new_end_time",
                    ],
                },
            },
        },
    ]


def _get_model_context_limit(model_name: str) -> int:
    """Retorna el límite de contexto del modelo. Para Gemini/Vertex es 1M tokens."""
    name_lower = model_name.lower()
    if "gemini" in name_lower:
        return 1000000
    return 1000000


async def chat_with_agent(
    agent_model_data: dict,
    conversation_history: list[dict],
    user_message: str,
    knowledge_context: str = "",
    db=None,
    agent_id: str = "",
) -> tuple[str, dict | None, bool, str | None, int, int]:
    """
    Envía un mensaje a Vertex AI y devuelve la respuesta junto con los datos
    de lead capturados, si se activó el handoff o si hubo una pregunta sin
    respuesta, y el conteo de tokens.

    Args:
        agent_model_data: configuración del agente (provider, model, system_prompt, ...).
        conversation_history: historial de mensajes previos.
        user_message: mensaje actual del usuario.
        knowledge_context: contexto RAG opcional.
        db: sesión de base de datos (opcional).
        agent_id: ID del agente (opcional).

    Returns:
        Tupla (respuesta, lead_data, handoff, unanswered_q, prompt_tokens, completion_tokens).
    """
    provider: str = agent_model_data.get("provider", "vertex")
    model_name: str = agent_model_data.get("model", "gemini-2.5-flash")
    system_prompt: str = agent_model_data.get("system_prompt", "")
    temperature: float = agent_model_data.get("temperature", 0.7)
    max_tokens: int = agent_model_data.get("max_tokens", 1024)
    custom_fields: list[dict] = agent_model_data.get("custom_fields", [])

    full_system_prompt = system_prompt
    if knowledge_context:
        full_system_prompt += (
            "\n\n[CONTEXTO DE NEGOCIO - Usa esta información para responder:]\n"
            f"{knowledge_context}"
        )

    messages: list[dict] = [{"role": "system", "content": full_system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

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

    calendar_connected = agent_model_data.get("google_calendar_connected", False)
    if calendar_connected:
        calendar_tools = build_calendar_tools()
        tools.extend(calendar_tools)
        for ct in calendar_tools:
            tool_origin_map[ct["function"]["name"]] = "calendar_builtin"

    final_text: str = ""
    lead_data: dict | None = None
    handoff_triggered: bool = False
    unanswered_question: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0

    try:
        max_allowed_chars = _get_model_context_limit(model_name) * 4
        run_messages = [dict(m) for m in messages]
        while len(run_messages) > 2 and sum(len(m.get("content") or "") for m in run_messages) > max_allowed_chars:
            run_messages.pop(1)

        from services.providers.vertex_provider import VertexAIProvider
        from services.providers.base import GenerationRequest, ProviderError

        vp = VertexAIProvider(model=model_name)
        req = GenerationRequest(
            messages=run_messages,
            system_prompt=full_system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        response_message = None
        tool_calls = None

        async def _vertex_call(req: GenerationRequest, max_retries: int = 2) -> GenerationRequest:
            nonlocal prompt_tokens, completion_tokens
            last_exc = None
            for attempt in range(max_retries):
                try:
                    result = await vp.generate(req, timeout_s=30.0)
                    prompt_tokens += result.input_tokens
                    completion_tokens += result.output_tokens
                    return result
                except (ProviderError, Exception) as exc:
                    last_exc = exc
                    logger.warning(
                        "Vertex AI intento %s/%s falló: %s", attempt + 1, max_retries, exc
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.5)
                        continue
            raise last_exc or Exception("Vertex AI no respondió tras reintentos")

        result = await _vertex_call(req)
        response_message = {"role": "assistant", "content": result.text}
        tool_calls = result.tool_calls if hasattr(result, "tool_calls") else None

        if tool_calls:
            run_messages.append(message_to_dict(response_message))

            for tool_call in tool_calls:
                func_name = tool_call.function.name
                args: dict = json.loads(tool_call.function.arguments)

                tool_result = await mcp_registry.execute_tool(
                    tool_name=func_name,
                    arguments=args,
                    tool_origin_map=tool_origin_map,
                    agent_id=agent_id,
                    db=db,
                )

                if func_name == "save_lead_info":
                    lead_data = args
                    logger.info("Datos de lead capturados: %s", args)
                elif func_name == "trigger_human_handoff":
                    handoff_triggered = True
                    logger.info("Human handoff triggered.")
                elif func_name == "alert_owner_about_unanswered_query":
                    unanswered_question = args.get("unanswered_question", user_message)
                    logger.info("Pregunta sin respuesta: %s", unanswered_question)

                run_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": json.dumps(tool_result),
                })

            second_call_messages: list[dict] = []
            for m in run_messages:
                role = m.get("role") if isinstance(m, dict) else getattr(m, "role", "user")
                content = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
                content = content or ""
                if role == "tool":
                    second_call_messages.append(
                        {"role": "user", "content": f"[Sistema: Información guardada exitosamente: {content}]"}
                    )
                elif role in ("assistant", "model"):
                    if content:
                        second_call_messages.append({"role": "assistant", "content": content})
                elif role in ("user", "system"):
                    second_call_messages.append({"role": role, "content": content})

            second_req = GenerationRequest(
                messages=second_call_messages,
                system_prompt=full_system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            second_result = await _vertex_call(second_req)
            final_text = second_result.text or ""
            prompt_tokens += second_result.input_tokens
            completion_tokens += second_result.output_tokens
        else:
            if isinstance(response_message, dict):
                final_text = response_message.get("content") or ""
            else:
                final_text = getattr(response_message, "content", "") or ""

        if final_text:
            final_text = re.sub(r"<function=\w+>.*?</function>", "", final_text, flags=re.DOTALL)
            final_text = re.sub(r"<function=\w+>.*$", "", final_text, flags=re.DOTALL)
            final_text = final_text.strip()

        if db:
            from services.model_rotation_service import ModelRotationService
            ModelRotationService.track_usage_and_check_limits(
                db=db, provider=provider, model=model_name,
                input_tokens=prompt_tokens, output_tokens=completion_tokens,
            )

    except Exception as exc:
        error_str = str(exc)
        logger.error("Error en chat_with_agent: %s", error_str, exc_info=True)
        if any(kw in error_str for kw in ("Quota exceeded", "429", "rate_limit", "RESOURCE_EXHAUSTED")):
            final_text = (
                "⚠️ El servicio de IA alcanzó su límite de cuota. "
                "Por favor, espera unos segundos e inténtalo de nuevo."
            )
        elif any(kw in error_str.lower() for kw in ("auth", "unauthorized", "401", "permission")):
            final_text = (
                "⚠️ Error de autenticación con el proveedor de IA. "
                "Contacta al administrador del sistema."
            )
        elif any(kw in error_str.lower() for kw in ("timeout", "timed out")):
            final_text = (
                "⚠️ El servicio de IA tardó demasiado en responder. "
                "Por favor, inténtalo de nuevo."
            )
        else:
            final_text = (
                "⚠️ Hubo un error procesando tu solicitud con el servicio de IA. "
                "Por favor, inténtalo de nuevo más tarde."
            )

    return (final_text, lead_data, handoff_triggered, unanswered_question, prompt_tokens, completion_tokens)


# ── Modelos disponibles (Vertex AI exclusivo) ────────────────────────


def get_available_models(provider: str) -> list[str]:
    """Retorna la lista de modelos disponibles para un proveedor (solo vertex/gemini)."""
    if provider in ("vertex", "gemini"):
        return ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    return []


# ── Delegacion en Model_Service (Vertex AI exclusivo) ───────────────


async def generate_via_model_service(
    messages: list[dict],
    system_prompt: str | None = None,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    usage_ctx=None,
):
    """
    Genera una respuesta delegando en `ModelService` (Vertex AI).

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
        ModelUnavailableError: Si el servicio falla (mapeable a 503).
    """
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


async def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/ogg",
    filename: str = "voice.ogg",
    stt_provider: str = "groq_whisper",
    language: str = "es",
) -> str:
    """
    Transcribe bytes de audio usando el proveedor STT configurado.

    Delega al servicio multi-proveedor stt_service.py.
    Mantiene compatibilidad con llamadas existentes.

    Args:
        audio_bytes: Bytes del audio.
        mime_type: Tipo MIME del audio.
        filename: Nombre del archivo.
        stt_provider: Proveedor STT ('groq_whisper', 'openai_whisper', 'deepgram', 'google_stt').
        language: Código de idioma (default: 'es').

    Returns:
        Texto transcrito.
    """
    from services.stt_service import transcribe_audio as stt_transcribe

    return await stt_transcribe(
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        filename=filename,
        stt_provider=stt_provider,
        language=language,
    )
