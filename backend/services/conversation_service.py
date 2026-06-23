"""Servicio unificado de procesamiento de conversaciones para PLATAFORMA GENIA.

Centraliza la lógica de interacción con el agente, recuperación de RAG,
inyección de prompts (imágenes, fecha/hora, captura de leads), persistencia de mensajes,
cálculo de costos y flujos de captura de leads y derivación humana (handoff).
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

    # 2. Cargar historial de chat (excluyendo el mensaje recién agregado)
    history_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.sent_at.asc())
        .all()
    )
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in history_messages
        if m.id is not None and m.id != user_msg.id
    ]

    # 3. Recuperar contexto semántico (RAG)
    knowledge_context = retrieve_context(agent_id=agent.id, query=user_message_text, db=db)

    # 4. Enriquecer el System Prompt
    system_prompt = agent.system_prompt or ""

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

    # 4.2 Inyectar fecha y hora local de Colombia (GMT-5)
    colombia_tz = timezone(timedelta(hours=-5))
    now_col = datetime.now(colombia_tz)
    dias_semana = {
        0: "lunes", 1: "martes", 2: "miércoles",
        3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"
    }
    system_prompt += (
        f"\n\n[FECHA Y HORA ACTUAL (GMT-5 Colombia)]\n"
        f"La fecha de hoy es: {now_col.strftime('%Y-%m-%d')}\n"
        f"El día de la semana es: {dias_semana[now_col.weekday()]}\n"
        f"La hora actual es: {now_col.strftime('%H:%M:%S')}\n"
        f"Usa esta información siempre que el usuario te pregunte por la fecha o la hora, o si necesitas calcular plazos, días o referencias temporales (como hoy, mañana, ayer, fin de semana, etc.).\n"
        f"IMPORTANTE: NO intentes llamar a herramientas o funciones externas para obtener fecha y hora (como get_current_date_and_time). Simplemente responde usando la información provista en este prompt."
    )

    # 4.3 Inyectar instrucciones de captura de leads incremental
    system_prompt += (
        "\n\n[INSTRUCCIONES DE CAPTURA DE LEADS]\n"
        "Debes llamar a la herramienta 'save_lead_info' de inmediato cada vez que el usuario te revele cualquier dato nuevo (como su nombre, su teléfono, su correo, o cualquier otro campo de interés como la empresa, tipo de espacio, temporalidad, etc.).\n"
        "NO esperes a tener todos los datos para llamar a la función. Ve guardando y actualizando los datos de forma incremental paso a paso a medida que fluye la conversación."
    )

    # 5. Preparar datos para el agente
    agent_data = {
        "provider": agent.provider,
        "model": agent.model,
        "system_prompt": system_prompt,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "custom_fields": agent.custom_fields,
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
                handoff_msg = (
                    f"⚠️ *¡Atención Requerida (Handoff)!*\n\n"
                    f"El cliente en la conversación con el agente *{agent.name}* ha solicitado hablar con un humano o se ha activado la derivación.\n\n"
                    f"Nombre del cliente: {conversation.contact_name or 'No especificado'}\n"
                    f"Teléfono: {conversation.contact_phone or 'No especificado'}\n"
                    f"Canal: {conversation.channel.upper()}\n"
                    f"ID Conversación: `{conversation.id}`\n\n"
                    f"Por favor, ve al panel de control para tomar el control de la conversación."
                )
                await send_whatsapp_notification(agent.notification_phone, handoff_msg)
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
