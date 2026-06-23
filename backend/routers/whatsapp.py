"""
Router de Webhooks de WhatsApp para PLATAFORMA GENIA.

Permite verificar el webhook de Meta y recibir mensajes entrantes de los clientes
asíncronamente en segundo plano para evitar time-outs de la API de Meta.
"""

from datetime import datetime, timezone, timedelta
import logging
from fastapi import APIRouter, Depends, Query, Request, Response, status, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from config import settings
from services.whatsapp_service import verify_whatsapp_signature, send_whatsapp_text
from models.agent import Agent
from models.conversation import Conversation, Message
from services.ai_service import chat_with_agent
from services.knowledge_service import retrieve_context
from services.lead_service import extract_and_save_lead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Integration"])


@router.get("/webhook")
def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Endpoint requerido por Meta para la verificación inicial del Webhook (Handshake).
    """
    if mode == "subscribe" and token == settings.webhook_verify_token:
        logger.info("[OK] Webhook de WhatsApp verificado exitosamente.")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning("Fallo en la verificación del Webhook de WhatsApp. Token inválido.")
    return Response(status_code=status.HTTP_403_FORBIDDEN)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook para recibir mensajes de WhatsApp desde Meta.
    Verifica la firma digital HMAC de Meta y procesa el mensaje de manera inline.
    """
    import os
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    
    # Validar firma HMAC
    if ENVIRONMENT == "production" and not settings.meta_app_secret:
        logger.error("Error de configuración: META_APP_SECRET no está definida en producción. Rechazando todos los webhooks.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de configuración del servidor: META_APP_SECRET no configurada.",
        )

    if settings.meta_app_secret or ENVIRONMENT == "production":
        if not verify_whatsapp_signature(body_bytes, signature, settings.meta_app_secret):
            logger.warning("Intento de webhook rechazado por firma HMAC no válida.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Firma HMAC no válida para el Webhook de WhatsApp.",
            )
            
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload JSON no válido.",
        )
        
    # Procesar webhook de manera síncrona/inline para Vercel Serverless
    try:
        await process_whatsapp_event(data, db)
    except Exception as e:
        logger.error(f"Error procesando evento de WhatsApp: {str(e)}", exc_info=True)
    
    return {"status": "accepted"}


async def process_whatsapp_event(data: dict, db: Session):
    """
    Procesador de eventos de WhatsApp inline.
    """
    if "entry" not in data:
        return
        
    for entry in data["entry"]:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" not in value:
                continue
                
            for msg in value["messages"]:
                phone_number = msg.get("from")
                msg_type = msg.get("type")
                whatsapp_msg_id = msg.get("id")
                
                if not phone_number or not whatsapp_msg_id:
                    continue
                    
                # 1. Validar tipos de mensaje (solo soportamos texto por ahora)
                if msg_type != "text":
                    logger.info(f"Mensaje de tipo {msg_type} recibido de {phone_number}. No soportado.")
                    await send_whatsapp_text(
                        phone_number,
                        "Lo siento, actualmente solo puedo comprender mensajes de texto."
                    )
                    continue
                    
                user_message_text = msg["text"].get("body", "")
                if not user_message_text.strip():
                    continue

                # Deduplicación: verificar si ya procesamos este mensaje
                from models.conversation import Message as DBMessage
                exists = db.query(DBMessage).filter(DBMessage.whatsapp_message_id == whatsapp_msg_id).first()
                if exists:
                    logger.info(f"Mensaje de WhatsApp con ID {whatsapp_msg_id} ya procesado. Ignorando duplicado.")
                    continue
                    
                # 2. Identificar el agente activo con canal 'whatsapp' habilitado
                agents = db.query(Agent).filter(Agent.status == "active").all()
                selected_agent = None
                for a in agents:
                    channels = a.channels or []
                    if "whatsapp" in channels:
                        selected_agent = a
                        break
                        
                if not selected_agent:
                    logger.warning("No se encontró ningún agente activo con canal 'whatsapp' habilitado.")
                    continue
                    
                # 3. Obtener o crear conversación de WhatsApp
                contact_name = "Usuario WhatsApp"
                contacts_list = value.get("contacts", [])
                if contacts_list:
                    contact_name = contacts_list[0].get("profile", {}).get("name", "Usuario WhatsApp")
                    
                conversation = (
                    db.query(Conversation)
                    .filter(
                        Conversation.agent_id == selected_agent.id,
                        Conversation.contact_phone == phone_number,
                        Conversation.channel == "whatsapp"
                    )
                    .first()
                )
                
                if not conversation:
                    conversation = Conversation(
                        agent_id=selected_agent.id,
                        contact_phone=phone_number,
                        contact_name=contact_name,
                        channel="whatsapp",
                        status="active"
                    )
                    db.add(conversation)
                    db.flush()
                    logger.info(f"Nueva conversación de WhatsApp creada: ID {conversation.id}")
                    
                # Si está en modo handoff, ignorar el mensaje en la IA para atención humana
                if conversation.status == "handoff":
                    logger.info(f"Conversación {conversation.id} en handoff. Ignorando IA.")
                    continue
                    
                # 4. Procesar el mensaje a través del servicio unificado de conversación
                from services.conversation_service import process_conversation_message
                
                reply = await process_conversation_message(
                    db=db,
                    agent=selected_agent,
                    conversation=conversation,
                    user_message_text=user_message_text,
                    source_channel="whatsapp",
                    whatsapp_message_id=whatsapp_msg_id
                )
                
                # 5. Enviar respuesta final por WhatsApp
                await send_whatsapp_text(phone_number, reply)
                logger.info(f"Respuesta enviada exitosamente a WhatsApp ({phone_number}).")
