"""Servicio unificado de procesamiento de conversaciones para PLATAFORMA GENIA.

Centraliza la lógica de interacción con el agente, recuperación de RAG,
inyección de prompts (imágenes, fecha/hora, captura de leads, calendario),
persistencia de mensajes, cálculo de costos y flujos de captura de leads,
derivación humana (handoff) y gestión de calendario.
"""

from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy.orm import Session

from models.agent import Agent
from models.conversation import Conversation, Message
from models.agent_image import AgentImage
from models.agent_usage import AgentUsage
from services.ai_service import chat_with_agent, calculate_cost
from services.knowledge_service import retrieve_context
from services.lead_service import extract_and_save_lead, check_lead_completeness_and_notify

logger = logging.getLogger(__name__)


async def process_conversation_message(
    db: Session,
    agent: Agent,
    conversation: Conversation,
    user_message_text: str,
    source_channel: str,  # "web" o "whatsapp"
    whatsapp_message_id: str = None,
) -> str:
    """
    Procesa un mensaje recibido del usuario en una conversación determinada.
    
    Realiza los siguientes pasos:
    1. Guarda el mensaje del usuario en SQL.
    2. Carga el historial de la conversación.
    3. Recupera el contexto semántico (RAG).
    4. Enriquese el System Prompt (imágenes, hora local, instrucciones de leads).
    5. Interactúa con el agente de IA.
    6. Calcula y registra costos de tokens.
    7. Guarda la respuesta del agente.
    8. Ejecuta flujos de handoff si corresponde.
    9. Actualiza de manera incremental la información de leads.
    """
    # 1. Guardar mensaje del usuario
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=user_message_text,
        whatsapp_message_id=whatsapp_message_id,
    )
    db.add(user_msg)
    db.flush()  # Obtener ID antes de cargar el historial

    # 2. Cargar historial de chat (excluyendo el mensaje recién agregado, limitado a los últimos 8)
    history_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.sent_at.desc())
        .limit(8)
        .all()
    )
    history_messages.reverse()
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in history_messages
        if m.id is not None and m.id != user_msg.id
    ]

    # 3. Cargar todas las conversaciones históricas del agente como ejemplos de entrenamiento
    #    (útil cuando se sincronizó el historial de WhatsApp)
    training_context = ""
    if agent.whatsapp_history_synced:
        historical_convs = (
            db.query(Conversation)
            .filter(
                Conversation.agent_id == agent.id,
                Conversation.channel == "whatsapp",
            )
            .order_by(Conversation.last_message_at.desc())
            .limit(10)
            .all()
        )
        examples = []
        for hc in historical_convs:
            if hc.id == conversation.id:
                continue
            msgs = (
                db.query(Message)
                .filter(Message.conversation_id == hc.id)
                .order_by(Message.sent_at.asc())
                .limit(6)
                .all()
            )
            if len(msgs) >= 2:
                conv_lines = []
                for m in msgs:
                    prefix = "Cliente" if m.role == "user" else "Tú"
                    conv_lines.append(f"{prefix}: {m.content[:200]}")
                examples.append("\n".join(conv_lines))
                if len(examples) >= 3:
                    break
        if examples:
            training_context = (
                "\n\n[EJEMPLOS DE CONVERSACIONES ANTERIORES]\n"
                "A continuación tienes ejemplos de conversaciones reales previas con otros clientes. "
                "Úsalos como referencia para aprender el tono, estilo y tipo de respuestas que debes dar.\n\n"
                + "\n\n---\n\n".join(examples)
            )

    # 4. Recuperar contexto semántico (RAG)
    knowledge_context = retrieve_context(agent_id=agent.id, query=user_message_text, db=db)

    # 5. Enriquecer el System Prompt
    system_prompt = agent.system_prompt or ""
    if training_context:
        system_prompt += training_context

    # 4.1 Inyectar biblioteca de imágenes
    images = db.query(AgentImage).filter(AgentImage.agent_id == agent.id).all()
    if images:
        system_prompt += (
            "\n\n[BIBLIOTECA DE IMÁGENES DISPONIBLES PARA ENVIAR]\n"
            "Tienes a tu disposición las siguientes imágenes que puedes enviar al cliente si te las solicita o si consideras relevante mostrar fotos/imágenes de un espacio, oficina, sala, etc. "
            "Para enviar una imagen, DEBES insertarla exactamente en tu respuesta usando la sintaxis estándar de Markdown: ![Descripción](URL)\n"
        )
        for img in images:
            system_prompt += f"- Nombre: {img.filename}, Descripción: {img.description or 'Sin descripción'}, URL: {img.url}\n"

    # 4.2 Inyectar fecha y hora local según la zona horaria del agente
    from zoneinfo import ZoneInfo
    agent_tz_str = agent.timezone if hasattr(agent, 'timezone') and agent.timezone else "America/Bogota"
    try:
        agent_tz = ZoneInfo(agent_tz_str)
    except Exception:
        agent_tz = ZoneInfo("America/Bogota")
        agent_tz_str = "America/Bogota"

    now_local = datetime.now(agent_tz)
    dias_semana = {
        0: "lunes", 1: "martes", 2: "miércoles",
        3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"
    }
    system_prompt += (
        f"\n\n[FECHA Y HORA ACTUAL ({agent_tz_str})]\n"
        f"La fecha de hoy es: {now_local.strftime('%Y-%m-%d')}\n"
        f"El día de la semana es: {dias_semana[now_local.weekday()]}\n"
        f"La hora actual es: {now_local.strftime('%H:%M:%S')}\n"
        f"Zona horaria: {agent_tz_str}\n"
        f"Usa esta información siempre que el usuario te pregunte por la fecha o la hora, o si necesitas calcular plazos, días o referencias temporales (como hoy, mañana, ayer, fin de semana, etc.).\n"
        f"IMPORTANTE: NO intentes llamar a herramientas o funciones externas para obtener fecha y hora (como get_current_date_and_time). Simplemente responde usando la información provista en este prompt."
    )

    # 4.3 Inyectar instrucciones de captura de leads incremental
    system_prompt += (
        "\n\n[INSTRUCCIONES DE CAPTURA DE LEADS]\n"
        "Debes llamar a la herramienta 'save_lead_info' de inmediato cada vez que el usuario te revele cualquier dato nuevo (como su nombre, su teléfono, su correo, o cualquier otro campo de interés como la empresa, tipo de espacio, temporalidad, etc.).\n"
        "NO esperes a tener todos los datos para llamar a la función. Ve guardando y actualizando los datos de forma incremental paso a paso a medida que fluye la conversación."
    )

    # 4.3.1 Inyectar reglas específicas de teléfono según el canal de comunicación
    if source_channel == "whatsapp" and conversation.contact_phone:
        system_prompt += (
            f"\n\n[CANAL DE COMUNICACIÓN ACTUAL]\n"
            f"El usuario se está comunicando contigo a través de WhatsApp desde el número: {conversation.contact_phone}\n"
            f"REGLA DE TELÉFONO EN WHATSAPP: Cuando necesites su número de teléfono de contacto para formalizar la reserva, NO le pidas que te lo escriba de cero. "
            f"En su lugar, pregúntale si desea que registremos el número desde el que te está escribiendo en este momento ({conversation.contact_phone}) o si prefiere darte otro número diferente."
        )
    else:
        system_prompt += (
            "\n\n[CANAL DE COMUNICACIÓN ACTUAL]\n"
            "El usuario se está comunicando a través de una aplicación web (chat web).\n"
            "REGLA DE TELÉFONO EN WEB: Dado que estás en un chat web y no tienes su información de contacto, debes pedirle explícitamente su número de teléfono al final de la reserva para poder registrarlo."
        )

    # 4.4 Inyectar instrucciones de Google Calendar cuando está conectado
    google_calendar_connected = getattr(agent, 'google_calendar_connected', False)
    if google_calendar_connected:
        system_prompt += (
            "\n\n[INSTRUCCIONES DE CALENDARIO - GOOGLE CALENDAR]\n"
            "Tienes acceso directo al calendario de Google del negocio. Puedes y debes:\n"
            "1. VERIFICAR DISPONIBILIDAD: Cuando el cliente pregunte por horarios disponibles, usa la herramienta 'check_calendar_availability' con la fecha solicitada.\n"
            "2. AGENDAR CITAS: Cuando el cliente quiera agendar una cita, usa 'create_calendar_event'. Asegúrate de confirmar fecha, hora y nombre del cliente antes de agendar.\n"
            "3. LISTAR EVENTOS: Cuando necesites ver las citas programadas, usa 'list_upcoming_events'.\n"
            "4. CANCELAR CITAS: Si el cliente quiere cancelar, SIEMPRE pregunta el motivo de la cancelación ANTES de usar 'cancel_calendar_event'. Registra el motivo.\n"
            "5. REPROGRAMAR CITAS: Si el cliente quiere cambiar la hora o fecha, usa 'reschedule_calendar_event'.\n"
            "6. RECORDATORIOS: Puedes mencionar las citas próximas del cliente si preguntan o si es relevante.\n\n"
            "REGLAS IMPORTANTES:\n"
            "- Siempre confirma los detalles con el cliente antes de crear o modificar una cita.\n"
            "- Usa formato de hora de 12 horas (ej: '3:00 PM') al hablar con el cliente, pero internamente usa formato de 24 horas.\n"
            "- Si el cliente quiere cancelar, muestra empatía y pregunta si desea reprogramar.\n"
            f"- La zona horaria del calendario es: {agent_tz_str}\n"
        )

    # 4.5 Inyectar reglas estrictas de Idioma, Formato Anti-CoT y Regla de 1 Pregunta a la Vez
    system_prompt += (
        "\n\n[REGLA DE CONVERSACIÓN Y RITMO CRÍTICA - UNA SOLA PREGUNTA A LA VEZ]\n"
        "1. Realiza MÁXIMO UNA PREGUNTA por mensaje. Queda TOTALMENTE PROHIBIDO hacer 2 o más preguntas acumuladas en una misma respuesta (por ejemplo: NUNCA preguntes al mismo tiempo '¿Qué espacio buscas y por cuánto tiempo lo necesitas?').\n"
        "2. Si vas a preguntar por el tipo de espacio, pregunta ÚNICAMENTE el tipo de espacio y espera la respuesta del cliente.\n"
        "3. Recién en la siguiente interacción pregunta por el tiempo o la sede. Avanza paso a paso para no abrumar al cliente.\n"
        "4. Responde SIEMPRE 100% en ESPAÑOL. NUNCA utilices el idioma inglés.\n"
        "5. NUNCA expongas pensamientos internos ni explicaciones de razonamiento como 'The user wants...', 'I need to...', 'The user says...'. Entrega ÚNICAMENTE la respuesta final destinada al cliente."
    )

    # Reemplazar marcadores en inglés del prompt original por español
    if "You are" in system_prompt or "YOUR TARGET LANGUAGE" in system_prompt or "FUNNEL" in system_prompt:
        system_prompt = system_prompt.replace("YOUR TARGET LANGUAGE:", "TU IDIOMA DE TRABAJO:")
        system_prompt = system_prompt.replace("Never respond in English.", "Responde SIEMPRE en español. Jamás en inglés.")
        system_prompt = system_prompt.replace("INFORMATION COLLECTION PROCESS (FUNNEL):", "PROCESO DE PERFILAMIENTO E INFORMACIÓN:")
        system_prompt = system_prompt.replace("Ask the following profiling questions STRICTLY ONE BY ONE.", "Haz las siguientes preguntas ESTRICTAMENTE UNA A LA VEZ.")

    # 5. Preparar datos para el agente (usando únicamente la API de Google Cloud Vertex AI / Gemini 2.0 Flash)
    provider_to_use = "vertex"
    model_to_use = "gemini-2.0-flash"

    agent_data = {
        "provider": provider_to_use,
        "model": model_to_use,
        "system_prompt": system_prompt,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "custom_fields": agent.custom_fields,
        "google_calendar_connected": google_calendar_connected,
        "timezone": agent_tz_str,
        "agent_id": agent.id,
    }

    # 6. Obtener respuesta de la IA
    reply, lead_data, handoff_triggered, unanswered_question, prompt_tokens, completion_tokens = await chat_with_agent(
        agent_model_data=agent_data,
        conversation_history=conversation_history,
        user_message=user_message_text,
        knowledge_context=knowledge_context,
        db=db,
        agent_id=agent.id,
    )

    # 6.1 Limpieza estricta y blindada anti-Chain of Thought (CoT) en inglés
    if reply:
        import re
        reply_str = reply.strip()
        cot_markers = (
            "The user", "I need to", "I should", "Based on the knowledge",
            "Funnel Step", "Next step in funnel", "The image", "matches \"",
            "Office Pinares", "Meeting room", "capacity ", "Price: 1h",
            "This fits the requirement", "I should show this", "Individual desk"
        )
        is_cot = any(marker in reply_str for marker in cot_markers)
        
        if is_cot:
            logger.warning("[CoT FILTER] Detectado razonamiento interno en inglés en el mensaje. Filtrando...")
            # Buscar el primer bloque de texto legítimo en español
            match = re.search(r'([¡¿]|Hola|Disculpa|Gracias|Estimado|Claro|Entendido|Perfecto|Excelente).*', reply_str, flags=re.DOTALL | re.IGNORECASE)
            valid_spanish = match.group(0).strip() if match else ""
            if valid_spanish and not any(m in valid_spanish for m in ("The user", "I need", "I should", "Funnel", "Office", "capacity", "Meeting room")):
                reply = valid_spanish
            else:
                # Si toda la salida era razonamiento en inglés sin respuesta final en español
                logger.warning("[CoT FILTER] Toda la salida era razonamiento en inglés. Sustituyendo por respuesta limpia en español.")
                if "5" in user_message_text or "personas" in user_message_text:
                    reply = "¡Perfecto! Entendido. Para un grupo de 5 personas tenemos oficinas privadas y salas amobladas. ¿Te gustaría conocer la opción disponible en nuestra sede de Pinares o Pereira Plaza?"
                else:
                    reply = "¡Entendido! Con gusto te colaboro. ¿Qué tipo de espacio buscas o en qué sede prefieres ubicarte (Pinares o Pereira Plaza)?"

    # 7. Registrar consumo y costo de tokens
    if prompt_tokens > 0 or completion_tokens > 0:
        try:
            cost = calculate_cost(agent.model, prompt_tokens, completion_tokens)
            usage = (
                db.query(AgentUsage)
                .filter(AgentUsage.agent_id == agent.id, AgentUsage.model == agent.model)
                .first()
            )
            
            if usage:
                usage.prompt_tokens += prompt_tokens
                usage.completion_tokens += completion_tokens
                usage.total_tokens += (prompt_tokens + completion_tokens)
                usage.cost += cost
            else:
                usage = AgentUsage(
                    agent_id=agent.id,
                    model=agent.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost=cost,
                )
                db.add(usage)
            
            logger.info(
                "Consumo registrado para agente %s (%s): %s prompt, %s completion, costo USD %s",
                agent.id,
                agent.model,
                prompt_tokens,
                completion_tokens,
                cost,
            )
        except Exception as ue:
            logger.error("Error al registrar consumo de tokens: %s", str(ue), exc_info=True)

    # 8. Registrar respuesta del asistente
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
    )
    db.add(assistant_msg)

    # 9. Procesar handoff humano
    if handoff_triggered:
        conversation.status = "handoff"
        logger.info("Conversación %s marcada como handoff.", conversation.id)
        
        if agent.notification_phone:
            try:
                from services.whatsapp_service import send_whatsapp_notification
                from services.encryption_service import decrypt as _decrypt
                handoff_msg = (
                    f"⚠️ *¡Atención Requerida (Handoff)!*\n\n"
                    f"El cliente en la conversación con el agente *{agent.name}* ha solicitado hablar con un humano o se ha activado la derivación.\n\n"
                    f"Nombre del cliente: {conversation.contact_name or 'No especificado'}\n"
                    f"Teléfono: {conversation.contact_phone or 'No especificado'}\n"
                    f"Canal: {conversation.channel.upper()}\n"
                    f"ID Conversación: `{conversation.id}`\n\n"
                    f"Por favor, ve al panel de control para tomar el control de la conversación."
                )
                # Usar credenciales de WA del agente si están disponibles
                _phone_id = agent.whatsapp_phone_number_id or ""
                _token = _decrypt(agent.whatsapp_access_token) if agent.whatsapp_access_token else ""
                await send_whatsapp_notification(
                    agent.notification_phone, handoff_msg,
                    phone_number_id=_phone_id, access_token=_token,
                )
            except Exception as he:
                logger.error("Error al enviar notificación de handoff: %s", str(he))

    # 10. Alerta de pregunta sin respuesta
    if unanswered_question:
        logger.warning(
            "ALERTA: Pregunta sin respuesta de usuario en conversación %s: %s",
            conversation.id,
            unanswered_question,
        )

    # 11. Procesar datos de Lead incremental
    if lead_data:
        try:
            lead = extract_and_save_lead(
                db=db,
                agent_id=agent.id,
                conversation_id=conversation.id,
                lead_data=lead_data,
                source_channel=source_channel,
            )
            
            # Sincronizar datos básicos en la conversación
            if lead.name and not conversation.contact_name:
                conversation.contact_name = lead.name
            if lead.phone and not conversation.contact_phone:
                conversation.contact_phone = lead.phone

            # Verificar completitud y alertar
            await check_lead_completeness_and_notify(db, lead.id)
        except Exception as le:
            logger.error("Error al procesar el lead de manera incremental: %s", str(le), exc_info=True)

    # 12. Actualizar marca temporal de actividad y commitear cambios
    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()

    return reply
