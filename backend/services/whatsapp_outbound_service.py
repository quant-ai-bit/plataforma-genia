"""
Servicio de Seguimiento Outbound Seguro para PLATAFORMA GENIA.

Maneja:
1. Sugerencia de mensajes de seguimiento (follow-up) personalizados con IA por lead.
2. Envío seguro 1 a 1 de mensajes outbound con simulación de escritura ("typing...").
3. Envío seguro en lotes pequeños (máximo 5) con retardos de 2 a 5 minutos entre envíos.
"""

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from models.agent import Agent
from models.contact import PreloadedContact
from models.lead import Lead
from models.conversation import Conversation, Message
from services.providers.vertex_provider import VertexAIProvider
from services.whatsapp_waha_service import send_waha_text, waha_is_mock_mode, _headers, _normalize_chat_id
from config import settings
import httpx

logger = logging.getLogger(__name__)

# Rastreador de cuota de envíos outbound en memoria (agent_id -> list of timestamps)
outbound_rate_tracker: Dict[str, List[datetime]] = {}

MAX_OUTBOUND_PER_HOUR = 5
MAX_OUTBOUND_PER_DAY = 15


def _check_outbound_quota(agent_id: str) -> Dict[str, Any]:
    """Verifica si el agente está dentro de los límites de seguridad outbound."""
    now = datetime.now(timezone.utc)
    history = outbound_rate_tracker.get(agent_id, [])

    # Filtrar envíos del último día y de la última hora
    one_day_ago = now - timedelta(days=1)
    one_hour_ago = now - timedelta(hours=1)

    recent_day = [t for t in history if t > one_day_ago]
    recent_hour = [t for t in history if t > one_hour_ago]

    outbound_rate_tracker[agent_id] = recent_day  # Limpiar antiguos

    if len(recent_hour) >= MAX_OUTBOUND_PER_HOUR:
        return {
            "allowed": False,
            "reason": f"Límite alcanzado: máximo {MAX_OUTBOUND_PER_HOUR} envíos outbound por hora para proteger tu cuenta de WhatsApp.",
        }
    if len(recent_day) >= MAX_OUTBOUND_PER_DAY:
        return {
            "allowed": False,
            "reason": f"Límite alcanzado: máximo {MAX_OUTBOUND_PER_DAY} envíos outbound por día para mantener una alta reputación.",
        }

    return {"allowed": True, "hourly_count": len(recent_hour), "daily_count": len(recent_day)}


def _record_outbound_send(agent_id: str):
    """Registra un envío outbound exitoso."""
    if agent_id not in outbound_rate_tracker:
        outbound_rate_tracker[agent_id] = []
    outbound_rate_tracker[agent_id].append(datetime.now(timezone.utc))


async def simulate_typing(session_name: str, phone: str, duration_seconds: float = 3.5):
    """Simula el estado 'Escribiendo...' (startTyping -> delay -> stopTyping) en WAHA."""
    if waha_is_mock_mode():
        await asyncio.sleep(1.0)
        return

    chat_id = _normalize_chat_id(phone)
    url_start = f"{settings.waha_api_url}/api/{session_name}/presence"
    headers = _headers()
    headers["Accept"] = "application/json"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Enviar presencia 'typing'
            await client.post(
                url_start,
                headers=headers,
                json={"session": session_name, "chatId": chat_id, "presence": "composing"},
            )
            # Esperar duración simulada
            await asyncio.sleep(duration_seconds)
            # Pausar presencia
            await client.post(
                url_start,
                headers=headers,
                json={"session": session_name, "chatId": chat_id, "presence": "paused"},
            )
    except Exception as ex:
        logger.warning(f"[OUTBOUND TYPING] No se pudo enviar señal de presencia: {ex}")
        await asyncio.sleep(duration_seconds)


async def suggest_followup_message(
    agent: Agent,
    phone: str,
    db: Session,
    custom_instruction: Optional[str] = None,
) -> Dict[str, Any]:
    """Genera una sugerencia de mensaje de seguimiento con IA adaptada al lead."""
    clean_phone = re.sub(r"\D", "", str(phone))

    # Buscar información del lead o contacto
    lead = db.query(Lead).filter(Lead.agent_id == agent.id, Lead.phone == clean_phone).first()
    contact = db.query(PreloadedContact).filter(PreloadedContact.agent_id == agent.id, PreloadedContact.phone == clean_phone).first()

    name = (lead.name if lead and lead.name else None) or (contact.name if contact and contact.name else "Cliente")
    nickname = getattr(contact, "nickname", None) if contact else None

    # Contexto de negocio del agente
    b_ctx = getattr(agent, "diagnostic_business_context", {}) or {}
    b_name = b_ctx.get("business_name") or agent.name
    b_type = b_ctx.get("business_type") or "Servicios Generales"

    # Buscar conversación existente
    conv = db.query(Conversation).filter(Conversation.agent_id == agent.id, Conversation.contact_phone == clean_phone).first()
    history_snippet = "Sin historial previo."
    if conv:
        recent_msgs = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.sent_at.desc()).limit(6).all()
        recent_msgs.reverse()
        if recent_msgs:
            history_snippet = "\n".join([f"{'DUEÑO' if m.role == 'assistant' else 'CLIENTE'}: {m.content[:150]}" for m in recent_msgs])

    prompt = f"""Eres el dueño del negocio '{b_name}' ({b_type}).
Redacta un mensaje de seguimiento (follow-up) cálido, profesional, personalizado y NO invasivo para WhatsApp.

DATOS DEL CLIENTE:
- Nombre: {name}
- Apodo detectado con el que sueles llamarlo: {nickname or 'Ninguno (usa el nombre formal o un saludo cálido)'}
- Teléfono: {clean_phone}

ÚLTIMOS MENSAJES DE LA CONVERSACIÓN:
{history_snippet}

INSTRUCCIÓN ADICIONAL DEL USUARIO:
{custom_instruction or 'Saluda de forma cercana, haz seguimiento sutil a su consulta anterior y ofrece ayuda.'}

REGLAS DE OBLIGATORIO CUMPLIMIENTO:
1. Sé breve (máximo 2 a 3 frases).
2. Si existe apodo ('{nickname}'), saluda dirigiéndote al cliente por ese apodo (ej: '¡Hola {nickname}!'). Si no hay apodo, usa su nombre ({name}).
3. Da continuidad a la conversación anterior sin presionar.
4. No uses lenguaje frío ni plantillas genéricas de correo.

Responde ÚNICAMENTE con el texto del mensaje listo para enviar."""

    try:
        vp = VertexAIProvider(model="gemini-2.5-flash")
        suggested_text = await vp.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return {
            "status": "success",
            "suggested_message": suggested_text.strip(),
            "target_name": name,
            "target_nickname": nickname,
            "phone": clean_phone,
        }
    except Exception as e:
        logger.error(f"[OUTBOUND SUGGEST] Error generando sugerencia para {clean_phone}: {e}")
        fallback_greeting = nickname or name or "hola"
        return {
            "status": "fallback",
            "suggested_message": f"¡Hola {fallback_greeting}! Quería dar seguimiento a nuestra conversación anterior. ¿Cómo vas con tu proyecto?",
            "target_name": name,
            "target_nickname": nickname,
            "phone": clean_phone,
        }


async def send_single_outbound(
    agent: Agent,
    phone: str,
    message_text: str,
    db: Session,
) -> Dict[str, Any]:
    """Envía un mensaje outbound manual 1 a 1 con simulación de typing y control de cuota."""
    # 1. Verificar cuotas
    quota_check = _check_outbound_quota(agent.id)
    if not quota_check["allowed"]:
        return {"status": "error", "error": quota_check["reason"]}

    clean_phone = re.sub(r"\D", "", str(phone))
    session_name = agent.whatsapp_qr_instance_name or f"genia_{agent.id[:8]}"

    # 2. Simular presencia 'typing...' (3 a 5 segundos)
    typing_duration = random.uniform(3.0, 5.0)
    await simulate_typing(session_name, clean_phone, duration_seconds=typing_duration)

    # 3. Enviar mensaje vía WAHA
    sent_ok = await send_waha_text(session_name, clean_phone, message_text)
    if not sent_ok:
        return {"status": "error", "error": "No se pudo entregar el mensaje a través del servidor de WhatsApp."}

    # 4. Registrar la cuota y guardar el mensaje en la BD de conversaciones
    _record_outbound_send(agent.id)

    conv = (
        db.query(Conversation)
        .filter(
            Conversation.agent_id == agent.id,
            Conversation.contact_phone == clean_phone,
        )
        .first()
    )
    if not conv:
        conv = Conversation(
            agent_id=agent.id,
            contact_phone=clean_phone,
            channel="whatsapp",
            status="active",
        )
        db.add(conv)
        db.flush()

    outbound_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=message_text,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(outbound_msg)
    conv.last_message_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"[OUTBOUND 1-TO-1] Mensaje enviado exitosamente a {clean_phone} para el agente {agent.id}")
    return {"status": "success", "message": "Mensaje outbound enviado correctamente."}


async def send_batch_outbound(
    agent: Agent,
    items: List[Dict[str, str]],  # [{"phone": "...", "message": "..."}, ...]
    db: Session,
) -> Dict[str, Any]:
    """
    Envía un lote pequeño de mensajes outbound (máximo 5) con retardos de 2 a 5 minutos
    entre cada uno para mantener el máximo nivel de seguridad frente a Meta.
    """
    if len(items) > 5:
        return {"status": "error", "error": "El lote supera el máximo permitido de 5 mensajes por lote."}

    sent_results = []
    for idx, item in enumerate(items):
        phone = item.get("phone")
        text = item.get("message")
        if not phone or not text:
            continue

        res = await send_single_outbound(agent, phone, text, db)
        sent_results.append({"phone": phone, "result": res})

        # Retardo defensivo de 2 a 4 minutos entre cada mensaje del lote
        if idx < len(items) - 1:
            delay_sec = random.randint(120, 240)
            logger.info(f"[BATCH OUTBOUND] Esperando {delay_sec}s antes de enviar el siguiente mensaje del lote...")
            await asyncio.sleep(delay_sec)

    return {"status": "success", "processed": len(sent_results), "details": sent_results}
