"""
Router de Webhooks de WhatsApp para PLATAFORMA GENIA.

Soporta integración multi-línea: cada agente tiene sus propias credenciales
de Meta (phone_number_id, access_token, app_secret, verify_token).

El webhook rutea los mensajes entrantes al agente correcto usando el
phone_number_id del payload de Meta.

Endpoints adicionales para conectar/desconectar/verificar WhatsApp
por agente desde el dashboard.
"""

from datetime import datetime, timezone, timedelta
import logging
from fastapi import APIRouter, Depends, Query, Request, Response, status, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from models.conversation import Conversation, Message
from services.whatsapp_service import (
    verify_whatsapp_signature,
    send_whatsapp_text,
    verify_whatsapp_connection,
    download_whatsapp_media,
)
from services.encryption_service import encrypt, decrypt
from services.ai_service import chat_with_agent
from services.knowledge_service import retrieve_context
from services.lead_service import extract_and_save_lead
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Integration"])


# ---------------------------------------------------------------------------
# Schemas para connect/disconnect
# ---------------------------------------------------------------------------

class WhatsAppConnectRequest(BaseModel):
    """Credenciales de Meta proporcionadas por el cliente para conectar WhatsApp."""
    phone_number_id: str = Field(..., min_length=1, description="Phone Number ID de la app de Meta")
    access_token: str = Field(..., min_length=1, description="Access Token permanente de Meta")
    app_secret: str = Field(..., min_length=1, description="App Secret de la app de Meta")
    verify_token: str = Field(
        default="genia_verify_token",
        description="Token personalizado para verificar el webhook",
    )


class WhatsAppStatusResponse(BaseModel):
    """Estado de conexión de WhatsApp para un agente."""
    connected: bool
    phone_number_id: str | None = None
    phone_number: str | None = None
    display_name: str | None = None
    webhook_url: str | None = None
    verify_token: str | None = None


# ---------------------------------------------------------------------------
# Webhook GET — Verificación de Meta (handshake)
# ---------------------------------------------------------------------------

@router.get("/webhook")
def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    """
    Endpoint requerido por Meta para la verificación inicial del Webhook (Handshake).

    Busca cualquier agente cuyo whatsapp_verify_token coincida con el token
    recibido. Si no se encuentra ninguno, se compara con el token global por
    retrocompatibilidad.
    """
    logger.info(f"[WEBHOOK_VERIFY] mode: {mode}, token: {token}, challenge: {challenge}")
    if mode != "subscribe":
        logger.warning(f"[WEBHOOK_VERIFY] Rejected mode: {mode}")
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    # 1. Buscar agente por verify_token personalizado
    agent = (
        db.query(Agent)
        .filter(
            Agent.whatsapp_verify_token == token,
            Agent.whatsapp_connected == True,
            Agent.status == "active",
        )
        .first()
    )

    if agent:
        logger.info(
            f"[OK] Webhook de WhatsApp verificado para agente '{agent.name}' "
            f"(phone_number_id={agent.whatsapp_phone_number_id})."
        )
        return Response(content=challenge, media_type="text/plain")

    # 2. Fallback: token global de settings (retrocompatibilidad)
    from config import settings
    if token == settings.webhook_verify_token:
        logger.info("[OK] Webhook de WhatsApp verificado con token global (legacy).")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Fallo en la verificación del Webhook de WhatsApp. Token inválido.")
    return Response(status_code=status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Webhook POST — Recepción de mensajes entrantes
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Webhook para recibir mensajes de WhatsApp desde Meta.

    Rutea los mensajes al agente correcto usando el phone_number_id
    del payload entrante y verifica la firma HMAC con el app_secret
    de ese agente.
    """
    import os
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload JSON no válido.",
        )

    # Extraer phone_number_id del payload de Meta para rutear al agente correcto
    incoming_phone_number_id = _extract_phone_number_id(data)

    if not incoming_phone_number_id:
        logger.warning("Webhook recibido sin phone_number_id en metadata. Ignorando.")
        return {"status": "ignored"}

    # Buscar el agente cuyo phone_number_id coincida
    agent = (
        db.query(Agent)
        .filter(
            Agent.whatsapp_phone_number_id == incoming_phone_number_id,
            Agent.whatsapp_connected == True,
            Agent.status == "active",
        )
        .first()
    )

    if not agent:
        # Fallback legacy: buscar con las credenciales globales de settings
        from config import settings
        if incoming_phone_number_id == settings.phone_number_id:
            # Modo legacy con credenciales globales
            await _process_legacy_webhook(data, body_bytes, signature, db, ENVIRONMENT)
            return {"status": "accepted"}

        logger.warning(
            f"No se encontró agente activo con phone_number_id={incoming_phone_number_id}. "
            "Ignorando webhook."
        )
        return {"status": "ignored"}

    # Descifrar credenciales del agente
    agent_app_secret = decrypt(agent.whatsapp_app_secret) if agent.whatsapp_app_secret else ""
    agent_access_token = decrypt(agent.whatsapp_access_token) if agent.whatsapp_access_token else ""

    # Validar firma HMAC con el app_secret del agente
    if agent_app_secret:
        if not verify_whatsapp_signature(body_bytes, signature, agent_app_secret):
            logger.warning(
                f"Firma HMAC inválida para agente '{agent.name}' "
                f"(phone_number_id={incoming_phone_number_id})."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Firma HMAC no válida para el Webhook de WhatsApp.",
            )
    elif ENVIRONMENT == "production":
        logger.error(
            f"Agente '{agent.name}' no tiene app_secret configurado en producción. "
            "Rechazando webhook."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de configuración: app_secret no configurado para este agente.",
        )

    # Procesar el evento
    try:
        await _process_agent_webhook(data, agent, agent_access_token, db)
    except Exception as e:
        logger.error(f"Error procesando evento de WhatsApp: {str(e)}", exc_info=True)

    return {"status": "accepted"}


# ---------------------------------------------------------------------------
# Endpoints de gestión de conexión WhatsApp por agente
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/connect")
async def connect_whatsapp(
    agent_id: str,
    body: WhatsAppConnectRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Conecta WhatsApp a un agente: valida las credenciales contra Meta,
    las cifra y las almacena.
    """
    # Buscar agente validando pertenencia
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    # Verificar que no haya otro agente con el mismo phone_number_id
    existing = (
        db.query(Agent)
        .filter(
            Agent.whatsapp_phone_number_id == body.phone_number_id,
            Agent.whatsapp_connected == True,
            Agent.id != agent_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El Phone Number ID {body.phone_number_id} ya está conectado "
                   f"al agente '{existing.name}'. Desconéctalo primero.",
        )

    # Verificar conexión con Meta
    verification = await verify_whatsapp_connection(
        phone_number_id=body.phone_number_id,
        access_token=body.access_token,
    )

    if not verification["connected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo verificar la conexión con Meta: {verification['error']}",
        )

    # Cifrar y almacenar credenciales
    agent.whatsapp_phone_number_id = body.phone_number_id
    agent.whatsapp_access_token = encrypt(body.access_token)
    agent.whatsapp_app_secret = encrypt(body.app_secret)
    agent.whatsapp_verify_token = body.verify_token
    agent.whatsapp_connected = True

    # Asegurar que 'whatsapp' esté en los canales del agente
    channels = agent.channels or []
    if "whatsapp" not in channels:
        agent.channels = channels + ["whatsapp"]

    db.commit()

    logger.info(
        f"WhatsApp conectado exitosamente para agente '{agent.name}' "
        f"(phone_number_id={body.phone_number_id}, "
        f"display_name={verification['display_name']})."
    )

    return {
        "status": "connected",
        "phone_number_id": body.phone_number_id,
        "phone_number": verification.get("phone_number"),
        "display_name": verification.get("display_name"),
        "quality_rating": verification.get("quality_rating"),
        "message": f"WhatsApp conectado exitosamente al agente '{agent.name}'.",
    }


@router.post("/{agent_id}/disconnect")
async def disconnect_whatsapp(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Desconecta WhatsApp de un agente: limpia las credenciales almacenadas.
    """
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    agent.whatsapp_phone_number_id = None
    agent.whatsapp_access_token = None
    agent.whatsapp_app_secret = None
    agent.whatsapp_verify_token = None
    agent.whatsapp_connected = False

    db.commit()

    logger.info(f"WhatsApp desconectado del agente '{agent.name}'.")

    return {
        "status": "disconnected",
        "message": f"WhatsApp desconectado del agente '{agent.name}'.",
    }


@router.get("/{agent_id}/status")
async def get_whatsapp_status(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna el estado de conexión de WhatsApp para un agente.
    No expone access_token ni app_secret.
    """
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    # Construir webhook URL (relativa; el frontend le añade el dominio)
    webhook_url = "/api/whatsapp/webhook"

    result = {
        "connected": agent.whatsapp_connected or False,
        "phone_number_id": agent.whatsapp_phone_number_id,
        "phone_number": None,
        "display_name": None,
        "webhook_url": webhook_url,
        "verify_token": agent.whatsapp_verify_token,
    }

    # Si está conectado, verificar con Meta en tiempo real
    if agent.whatsapp_connected and agent.whatsapp_access_token:
        access_token = decrypt(agent.whatsapp_access_token)
        if access_token:
            verification = await verify_whatsapp_connection(
                phone_number_id=agent.whatsapp_phone_number_id,
                access_token=access_token,
            )
            result["phone_number"] = verification.get("phone_number")
            result["display_name"] = verification.get("display_name")
            # Si Meta reporta error, marcar como desconectado
            if not verification["connected"]:
                result["connected"] = False
                result["error"] = verification.get("error")

    return result


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _extract_phone_number_id(data: dict) -> str | None:
    """Extrae el phone_number_id del payload del webhook de Meta."""
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id")
                if phone_number_id:
                    return phone_number_id
    except Exception:
        pass
    return None


async def _process_agent_webhook(
    data: dict,
    agent: Agent,
    access_token: str,
    db: Session,
):
    """
    Procesa un evento de WhatsApp para un agente específico con sus credenciales.
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

                # Soportar texto y notas de voz (audio)
                user_message_text = ""

                if msg_type == "audio":
                    logger.info(
                        f"Recibida nota de voz de {phone_number} para agente '{agent.name}'. "
                        "Procesando transcripción..."
                    )
                    audio_data = msg.get("audio", {})
                    media_id = audio_data.get("id")
                    mime_type = audio_data.get("mime_type", "audio/ogg")

                    if not media_id:
                        logger.warning("Mensaje de tipo audio recibido sin media ID. Ignorando.")
                        continue

                    try:
                        # 1. Descargar audio de los servidores de Meta
                        audio_bytes = await download_whatsapp_media(media_id, access_token)

                        # 2. Determinar la extensión
                        ext = "ogg"
                        if "mpeg" in mime_type or "mp3" in mime_type:
                            ext = "mp3"
                        elif "m4a" in mime_type:
                            ext = "m4a"

                        # 3. Transcribir usando Groq Whisper
                        from services.ai_service import transcribe_audio
                        user_message_text = await transcribe_audio(
                            audio_bytes=audio_bytes,
                            mime_type=mime_type,
                            filename=f"voice.{ext}"
                        )
                        logger.info(
                            f"Transcripción exitosa para {phone_number}: \"{user_message_text}\""
                        )
                    except Exception as e:
                        logger.error(
                            f"Error procesando nota de voz de {phone_number}: {str(e)}",
                            exc_info=True
                        )
                        await send_whatsapp_text(
                            phone_number,
                            "Lo siento, tuve un problema al escuchar tu nota de voz. ¿Podrías escribirme la consulta o intentar de nuevo?",
                            agent.whatsapp_phone_number_id,
                            access_token,
                        )
                        continue
                elif msg_type == "text":
                    user_message_text = msg["text"].get("body", "")
                else:
                    logger.info(
                        f"Mensaje de tipo {msg_type} recibido de {phone_number} "
                        f"para agente '{agent.name}'. No soportado."
                    )
                    await send_whatsapp_text(
                        phone_number,
                        "Lo siento, por ahora solo puedo entender mensajes de texto y notas de voz.",
                        agent.whatsapp_phone_number_id,
                        access_token,
                    )
                    continue

                if not user_message_text.strip():
                    continue


                # Deduplicación
                from models.conversation import Message as DBMessage
                exists = (
                    db.query(DBMessage)
                    .filter(DBMessage.whatsapp_message_id == whatsapp_msg_id)
                    .first()
                )
                if exists:
                    logger.info(
                        f"Mensaje WhatsApp {whatsapp_msg_id} ya procesado. "
                        "Ignorando duplicado."
                    )
                    continue

                # Obtener o crear conversación
                contact_name = "Usuario WhatsApp"
                contacts_list = value.get("contacts", [])
                if contacts_list:
                    contact_name = (
                        contacts_list[0]
                        .get("profile", {})
                        .get("name", "Usuario WhatsApp")
                    )

                conversation = (
                    db.query(Conversation)
                    .filter(
                        Conversation.agent_id == agent.id,
                        Conversation.contact_phone == phone_number,
                        Conversation.channel == "whatsapp",
                    )
                    .first()
                )

                if not conversation:
                    conversation = Conversation(
                        agent_id=agent.id,
                        contact_phone=phone_number,
                        contact_name=contact_name,
                        channel="whatsapp",
                        status="active",
                    )
                    db.add(conversation)
                    db.flush()
                    logger.info(
                        f"Nueva conversación WhatsApp creada: ID {conversation.id} "
                        f"para agente '{agent.name}'"
                    )

                # Si está en modo handoff, ignorar
                if conversation.status == "handoff":
                    logger.info(
                        f"Conversación {conversation.id} en handoff. Ignorando IA."
                    )
                    continue

                # Procesar a través del servicio unificado
                from services.conversation_service import process_conversation_message

                reply = await process_conversation_message(
                    db=db,
                    agent=agent,
                    conversation=conversation,
                    user_message_text=user_message_text,
                    source_channel="whatsapp",
                    whatsapp_message_id=whatsapp_msg_id,
                )

                # Enviar respuesta con las credenciales del agente
                await send_whatsapp_text(
                    phone_number,
                    reply,
                    agent.whatsapp_phone_number_id,
                    access_token,
                )
                logger.info(
                    f"Respuesta enviada a WhatsApp ({phone_number}) "
                    f"via agente '{agent.name}'."
                )


async def _process_legacy_webhook(
    data: dict,
    body_bytes: bytes,
    signature: str | None,
    db: Session,
    environment: str,
):
    """
    Procesamiento legacy usando credenciales globales de settings.
    Mantiene retrocompatibilidad con la configuración anterior.
    """
    from config import settings

    # Validar firma HMAC con settings globales
    if settings.meta_app_secret or environment == "production":
        if not settings.meta_app_secret and environment == "production":
            logger.error(
                "META_APP_SECRET no definida en producción. Rechazando webhook."
            )
            return
        if not verify_whatsapp_signature(
            body_bytes, signature, settings.meta_app_secret
        ):
            logger.warning("Firma HMAC inválida (modo legacy).")
            return

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

                if msg_type != "text":
                    logger.info(
                        f"Mensaje de tipo {msg_type} recibido de {phone_number}. "
                        "No soportado."
                    )
                    await send_whatsapp_text(
                        phone_number,
                        "Lo siento, actualmente solo puedo comprender mensajes de texto.",
                        settings.phone_number_id,
                        settings.meta_access_token,
                    )
                    continue

                user_message_text = msg["text"].get("body", "")
                if not user_message_text.strip():
                    continue

                # Deduplicación
                from models.conversation import Message as DBMessage
                exists = (
                    db.query(DBMessage)
                    .filter(DBMessage.whatsapp_message_id == whatsapp_msg_id)
                    .first()
                )
                if exists:
                    continue

                # Buscar agente activo con canal whatsapp (legacy)
                agents = (
                    db.query(Agent)
                    .filter(Agent.status == "active")
                    .all()
                )
                selected_agent = None
                for a in agents:
                    channels = a.channels or []
                    if "whatsapp" in channels:
                        selected_agent = a
                        break

                if not selected_agent:
                    logger.warning(
                        "No se encontró ningún agente activo con canal "
                        "'whatsapp' habilitado (legacy)."
                    )
                    continue

                contact_name = "Usuario WhatsApp"
                contacts_list = value.get("contacts", [])
                if contacts_list:
                    contact_name = (
                        contacts_list[0]
                        .get("profile", {})
                        .get("name", "Usuario WhatsApp")
                    )

                conversation = (
                    db.query(Conversation)
                    .filter(
                        Conversation.agent_id == selected_agent.id,
                        Conversation.contact_phone == phone_number,
                        Conversation.channel == "whatsapp",
                    )
                    .first()
                )

                if not conversation:
                    conversation = Conversation(
                        agent_id=selected_agent.id,
                        contact_phone=phone_number,
                        contact_name=contact_name,
                        channel="whatsapp",
                        status="active",
                    )
                    db.add(conversation)
                    db.flush()

                if conversation.status == "handoff":
                    continue

                from services.conversation_service import process_conversation_message

                reply = await process_conversation_message(
                    db=db,
                    agent=selected_agent,
                    conversation=conversation,
                    user_message_text=user_message_text,
                    source_channel="whatsapp",
                    whatsapp_message_id=whatsapp_msg_id,
                )

                await send_whatsapp_text(
                    phone_number,
                    reply,
                    settings.phone_number_id,
                    settings.meta_access_token,
                )
