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
import httpx
from fastapi import APIRouter, Depends, Query, Request, Response, status, HTTPException

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from config import settings
from models.agent import Agent
from models.conversation import Conversation, Message

from services.whatsapp_service import (
    verify_whatsapp_signature,
    send_whatsapp_text,
    verify_whatsapp_connection,
    download_whatsapp_media,
)
from services.whatsapp_qr_service import (
    create_qr_instance,
    get_qr_code,
    verify_qr_connection,
    delete_qr_instance,
    send_qr_text,
    configure_qr_webhook,
    simulate_qr_scan,
    is_mock_mode as qr_is_mock_mode,
)
from services.encryption_service import encrypt, decrypt
from services.ai_service import chat_with_agent
from services.knowledge_service import retrieve_context
from services.lead_service import extract_and_save_lead
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Integration"])


# #region debug-point shared:reporter
def _report_debug_event(
    hypothesis_id: str,
    location: str,
    msg: str,
    data: dict | None = None,
    run_id: str = "pre-fix",
):
    try:
        import json as _json
        import urllib.request as _urlreq

        env_path = ".dbg/whatsapp-no-response.env"
        debug_url = "http://127.0.0.1:7777/event"
        session_id = "whatsapp-no-response"
        try:
            with open(env_path, "r", encoding="utf-8") as env_file:
                env_content = env_file.read().splitlines()
            for line in env_content:
                if line.startswith("DEBUG_SERVER_URL="):
                    debug_url = line.split("=", 1)[1].strip()
                elif line.startswith("DEBUG_SESSION_ID="):
                    session_id = line.split("=", 1)[1].strip()
        except Exception:
            pass

        payload = {
            "sessionId": session_id,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "msg": f"[DEBUG] {msg}",
            "data": data or {},
        }
        request = _urlreq.Request(
            debug_url,
            data=_json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        _urlreq.urlopen(request, timeout=1).read()
    except Exception:
        pass


# #endregion
#
# ---------------------------------------------------------------------------
# Schemas para connect/disconnect
# ---------------------------------------------------------------------------


class WhatsAppConnectRequest(BaseModel):
    """Credenciales de Meta proporcionadas por el cliente para conectar WhatsApp."""

    phone_number_id: str = Field(
        ..., min_length=1, description="Phone Number ID de la app de Meta"
    )
    access_token: str = Field(
        ..., min_length=1, description="Access Token permanente de Meta"
    )
    app_secret: str = Field(
        ..., min_length=1, description="App Secret de la app de Meta"
    )
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
    whatsapp_provider: str | None = None
    whatsapp_qr_connected: bool | None = None
    whatsapp_qr_instance_name: str | None = None
    qr_code: str | None = None
    is_mock_mode: bool | None = None


class WhatsAppProviderRequest(BaseModel):
    """Request para cambiar de proveedor de WhatsApp."""

    provider: str = Field(..., description="Proveedor: 'meta_cloud' o 'qr_code'")


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
    logger.info(
        f"[WEBHOOK_VERIFY] mode: {mode}, token: {token}, challenge: {challenge}"
    )
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
    agent_app_secret = (
        decrypt(agent.whatsapp_app_secret) if agent.whatsapp_app_secret else ""
    )
    agent_access_token = (
        decrypt(agent.whatsapp_access_token) if agent.whatsapp_access_token else ""
    )

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
    Soporta los proveedores 'meta_cloud' y 'qr_code'.
    No expone tokens ni claves.
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

    whatsapp_provider = agent.whatsapp_provider or "meta_cloud"
    webhook_url = (
        "/api/whatsapp/webhook"
        if whatsapp_provider == "meta_cloud"
        else f"/api/whatsapp/webhook/qr/{agent.id}"
    )

    result = {
        "connected": False,
        "phone_number_id": agent.whatsapp_phone_number_id,
        "phone_number": None,
        "display_name": None,
        "webhook_url": webhook_url,
        "verify_token": agent.whatsapp_verify_token,
        "whatsapp_provider": whatsapp_provider,
        "whatsapp_qr_connected": agent.whatsapp_qr_connected or False,
        "whatsapp_qr_instance_name": agent.whatsapp_qr_instance_name,
        "qr_code": None,
        "is_mock_mode": qr_is_mock_mode(),
    }

    if whatsapp_provider == "meta_cloud":
        result["connected"] = agent.whatsapp_connected or False
        if agent.whatsapp_connected and agent.whatsapp_access_token:
            access_token = decrypt(agent.whatsapp_access_token)
            if access_token:
                verification = await verify_whatsapp_connection(
                    phone_number_id=agent.whatsapp_phone_number_id,
                    access_token=access_token,
                )
                result["phone_number"] = verification.get("phone_number")
                result["display_name"] = verification.get("display_name")
                if not verification["connected"]:
                    result["connected"] = False
                    result["error"] = verification.get("error")
    else:
        # QR Code Provider
        if agent.whatsapp_qr_instance_name:
            verification = await verify_qr_connection(agent.whatsapp_qr_instance_name)
            result["connected"] = verification["connected"]
            result["whatsapp_qr_connected"] = verification["connected"]
            result["phone_number"] = verification.get("phone_number")
            result["display_name"] = verification.get("display_name")
            result["error"] = verification.get("error")

            # Si no está conectado, obtener el QR para mostrarlo en el frontend
            if not verification["connected"]:
                result["qr_code"] = await get_qr_code(agent.whatsapp_qr_instance_name)
            else:
                result["qr_code"] = None

            # Actualizar DB si el estado cambió
            if agent.whatsapp_qr_connected != verification["connected"]:
                agent.whatsapp_qr_connected = verification["connected"]
                db.commit()
        else:
            result["connected"] = False
            result["whatsapp_qr_connected"] = False

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
                        logger.warning(
                            "Mensaje de tipo audio recibido sin media ID. Ignorando."
                        )
                        continue

                    try:
                        # 1. Descargar audio de los servidores de Meta
                        audio_bytes = await download_whatsapp_media(
                            media_id, access_token
                        )

                        # 2. Determinar la extensión
                        ext = "ogg"
                        if "mpeg" in mime_type or "mp3" in mime_type:
                            ext = "mp3"
                        elif "m4a" in mime_type:
                            ext = "m4a"

                        # 3. Transcribir usando el proveedor configurado del agente
                        from services.ai_service import transcribe_audio

                        user_message_text = await transcribe_audio(
                            audio_bytes=audio_bytes,
                            mime_type=mime_type,
                            filename=f"voice.{ext}",
                            stt_provider=agent.stt_provider
                            if hasattr(agent, "stt_provider") and agent.stt_provider
                            else "groq_whisper",
                        )
                        logger.info(
                            f'Transcripción exitosa para {phone_number}: "{user_message_text}"'
                        )
                    except Exception as e:
                        logger.error(
                            f"Error procesando nota de voz de {phone_number}: {str(e)}",
                            exc_info=True,
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
                agents = db.query(Agent).filter(Agent.status == "active").all()
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


# ---------------------------------------------------------------------------
# Endpoints adicionales para WhatsApp QR Code (Evolution API)
# ---------------------------------------------------------------------------


@router.post("/{agent_id}/provider")
async def update_whatsapp_provider(
    agent_id: str,
    body: WhatsAppProviderRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cambia el proveedor de WhatsApp entre 'meta_cloud' y 'qr_code'."""
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    if body.provider not in ["meta_cloud", "qr_code"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proveedor no válido. Debe ser 'meta_cloud' o 'qr_code'.",
        )

    agent.whatsapp_provider = body.provider
    db.commit()

    logger.info(
        f"Proveedor de WhatsApp cambiado a '{body.provider}' para agente '{agent.name}'."
    )
    return {
        "status": "success",
        "whatsapp_provider": body.provider,
        "message": f"Proveedor de WhatsApp cambiado a '{body.provider}' exitosamente.",
    }


@router.post("/{agent_id}/qr/connect")
async def connect_whatsapp_qr(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Inicializa una sesión QR (Evolution API) para vincular el agente.
    Genera el código QR base64 inicial y configura el webhook.
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

    # Definir nombre de instancia único para evitar colisiones de caché de Baileys
    import time
    instance_name = f"genia_{agent.id[:8]}_{int(time.time())}"
    agent.whatsapp_qr_instance_name = instance_name

    # Intentar inicializar instancia
    init_res = await create_qr_instance(instance_name)
    if init_res["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear la sesión QR: {init_res['error']}",
        )

    if "token" in init_res and init_res["token"]:
        agent.whatsapp_qr_instance_token = encrypt(init_res["token"])

    # Configurar Webhook apuntando dinámicamente al host actual de la petición
    base_url = str(request.base_url).rstrip("/")
    webhook_url = f"{base_url}/api/whatsapp/webhook/qr/{agent.id}"
    await configure_qr_webhook(instance_name, webhook_url)

    # Obtener el primer QR
    qr_code = await get_qr_code(instance_name)

    agent.whatsapp_provider = "qr_code"
    # Asegurar que 'whatsapp' esté en los canales
    channels = agent.channels or []
    if "whatsapp" not in channels:
        agent.channels = channels + ["whatsapp"]

    db.commit()

    return {
        "status": "connecting",
        "instance_name": instance_name,
        "qr_code": qr_code,
        "message": "Escanea el código QR desde tu celular en WhatsApp > Dispositivos Vinculados.",
    }


@router.post("/{agent_id}/qr/disconnect")
async def disconnect_whatsapp_qr(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Desconecta la línea QR y destruye la instancia."""
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    if agent.whatsapp_qr_instance_name:
        await delete_qr_instance(agent.whatsapp_qr_instance_name)

    agent.whatsapp_qr_instance_name = None
    agent.whatsapp_qr_instance_token = None
    agent.whatsapp_qr_connected = False
    db.commit()

    logger.info(f"WhatsApp QR desconectado para agente '{agent.name}'.")
    return {
        "status": "disconnected",
        "message": f"WhatsApp QR desconectado del agente '{agent.name}'.",
    }


@router.post("/{agent_id}/qr/simulate-scan")
async def simulate_scan_qr(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Endpoint de utilidad para pruebas en desarrollo.
    Simula que el usuario escaneó el QR en el móvil y conecta el webhook de inmediato.
    """
    if not qr_is_mock_mode():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La simulación de escaneo solo está disponible en modo de desarrollo local sin Evolution API.",
        )

    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    instance_name = agent.whatsapp_qr_instance_name or f"genia_agent_{agent.id}"
    simulate_qr_scan(instance_name)
    agent.whatsapp_qr_connected = True
    db.commit()

    logger.info(f"[SIMULACIÓN] QR escaneado con éxito para agente '{agent.name}'.")
    return {
        "status": "connected",
        "message": f"Línea de WhatsApp QR simulada y conectada para el agente '{agent.name}'.",
    }


@router.post("/webhook/qr/{agent_id}")
async def receive_qr_webhook(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Webhook para recibir mensajes de WhatsApp desde la API de emulación (Código QR).
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload JSON no válido.",
        )

    # #region debug-point B:webhook-entry
    _report_debug_event(
        hypothesis_id="B",
        location="backend/routers/whatsapp.py:receive_qr_webhook",
        msg="QR webhook recibido",
        data={
            "agent_id": agent_id,
            "event": data.get("event") if isinstance(data, dict) else None,
            "top_keys": list(data.keys())[:10] if isinstance(data, dict) else [],
        },
    )
    # #endregion

    # ── PAYLOAD DEBUG LOGGING TO DB ──
    try:
        from models.conversation import Conversation as DBConv, Message as DBMessage
        import json as _json
        from datetime import datetime, timezone
        import uuid

        # Search for debug conversation
        debug_conv = (
            db.query(DBConv).filter(DBConv.contact_phone == "PAYLOAD_DEBUG").first()
        )
        if not debug_conv:
            debug_conv = DBConv(
                id=uuid.uuid4().hex,
                agent_id=agent_id,
                contact_phone="PAYLOAD_DEBUG",
                contact_name="Payload Debugger",
                channel="whatsapp",
                status="active",
                started_at=datetime.now(timezone.utc),
                last_message_at=datetime.now(timezone.utc),
            )
            db.add(debug_conv)
            db.commit()
            db.refresh(debug_conv)

        # Log payload as a message
        payload_str = _json.dumps(data)
        debug_msg = DBMessage(
            id=uuid.uuid4().hex,
            conversation_id=debug_conv.id,
            role="user",
            content=f"Agent: {agent_id} | Payload: {payload_str}"[
                :3000
            ],  # cap to avoid column limits
            sent_at=datetime.now(timezone.utc),
        )
        db.add(debug_msg)
        db.commit()
    except Exception as db_err:
        print("[DEBUG LOG ERROR]", str(db_err))

    try:
        return await _receive_qr_webhook_impl(agent_id, request, db, data)
    except Exception as e:
        import traceback

        err_msg = traceback.format_exc()
        logger.error(f"[QR WEBHOOK ERROR] Agent {agent_id}: {err_msg}")
        try:
            debug_conv = (
                db.query(DBConv).filter(DBConv.contact_phone == "PAYLOAD_DEBUG").first()
            )
            if debug_conv:
                debug_msg = DBMessage(
                    id=uuid.uuid4().hex,
                    conversation_id=debug_conv.id,
                    role="assistant",
                    content=f"ERROR TRACEBACK: {err_msg}"[:3000],
                    sent_at=datetime.now(timezone.utc),
                )
                db.add(debug_msg)
                db.commit()
        except Exception:
            pass
        return {
            "status": "accepted",
            "warning": f"Error interno procesado: {str(e)[:200]}",
        }


async def _receive_qr_webhook_impl(
    agent_id: str,
    request: Request,
    db: Session,
    data: dict,
):
    # Log completo del payload para depuración
    import json as _json

    logger.info(
        f"[QR WEBHOOK] Payload recibido: event={data.get('event')}, keys={list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
    )
    logger.info(
        f"[QR WEBHOOK] data type={type(data.get('data')).__name__ if isinstance(data, dict) else 'N/A'}, raw_data_preview={str(data)[:500]}"
    )

    agent = (
        db.query(Agent).filter(Agent.id == agent_id, Agent.status == "active").first()
    )
    if not agent:
        # #region debug-point E:agent-not-found
        _report_debug_event(
            hypothesis_id="E",
            location="backend/routers/whatsapp.py:_receive_qr_webhook_impl",
            msg="Webhook QR ignorado por agente inexistente o inactivo",
            data={"agent_id": agent_id},
        )
        # #endregion
        logger.warning(
            f"Webhook QR recibido para agente inexistente o inactivo: {agent_id}"
        )
        return {"status": "ignored"}

    # #region debug-point E:agent-state
    _report_debug_event(
        hypothesis_id="E",
        location="backend/routers/whatsapp.py:_receive_qr_webhook_impl",
        msg="Estado base del agente QR cargado",
        data={
            "agent_id": agent.id,
            "agent_name": agent.name,
            "status": agent.status,
            "provider": agent.whatsapp_provider,
            "qr_connected": agent.whatsapp_qr_connected,
            "instance_name": agent.whatsapp_qr_instance_name,
        },
    )
    # #endregion

    # Extraer detalles
    details = _extract_qr_message_details(data)
    if not details:
        # #region debug-point A:details-empty
        _report_debug_event(
            hypothesis_id="A",
            location="backend/routers/whatsapp.py:_receive_qr_webhook_impl",
            msg="No se pudieron extraer detalles del mensaje QR",
            data={
                "agent_id": agent.id,
                "event": data.get("event") if isinstance(data, dict) else None,
                "data_type": type(data.get("data")).__name__
                if isinstance(data, dict)
                else None,
            },
        )
        # #endregion
        # Evento administrativo
        event_type = data.get("event")
        if event_type == "connection.update":
            state = data.get("data", {}).get("state")
            if state == "open":
                agent.whatsapp_qr_connected = True
                db.commit()
                logger.info(
                    f"Línea QR de agente '{agent.name}' marcada como CONECTADA."
                )
            elif state in ["close", "refused"]:
                agent.whatsapp_qr_connected = False
                db.commit()
                logger.info(
                    f"Línea QR de agente '{agent.name}' marcada como DESCONECTADA."
                )
        return {"status": "accepted"}

    phone_number = details["phone_number"]
    whatsapp_msg_id = details["whatsapp_msg_id"]
    user_message_text = details["text"]
    msg_type = details["type"]
    push_name = details["push_name"]

    # #region debug-point C:details-extracted
    _report_debug_event(
        hypothesis_id="C",
        location="backend/routers/whatsapp.py:_receive_qr_webhook_impl",
        msg="Detalles del mensaje QR extraídos",
        data={
            "agent_id": agent.id,
            "phone_number": phone_number,
            "whatsapp_msg_id": whatsapp_msg_id,
            "msg_type": msg_type,
            "text_preview": user_message_text[:80],
            "push_name": push_name,
        },
    )
    # #endregion

    # Deduplicar
    from models.conversation import Message as DBMessage

    exists = (
        db.query(DBMessage)
        .filter(DBMessage.whatsapp_message_id == whatsapp_msg_id)
        .first()
    )
    if exists:
        return {"status": "ignored"}

    # Obtener/crear conversación
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
            contact_name=push_name,
            channel="whatsapp",
            status="active",
        )
        db.add(conversation)
        db.flush()

    if conversation.status == "handoff":
        should_reactivate = False
        if conversation.last_message_at:
            now_tz = datetime.now(timezone.utc)
            last_msg_at = conversation.last_message_at
            if last_msg_at.tzinfo is None:
                last_msg_at = last_msg_at.replace(tzinfo=timezone.utc)
            if now_tz - last_msg_at > timedelta(minutes=2):
                should_reactivate = True

        # También si envían un saludo/comando de reinicio
        if user_message_text and user_message_text.strip().lower() in [
            "hola",
            "reiniciar",
            "reinicia",
            "iniciar",
        ]:
            should_reactivate = True

        if should_reactivate:
            conversation.status = "active"
            db.commit()
            logger.info(
                f"Conversación QR {conversation.id} reactivada automáticamente de handoff a active."
            )
        else:
            logger.info(f"Conversación QR {conversation.id} en handoff. Ignorando IA.")
            return {"status": "ignored"}

    # Nota de voz
    if msg_type == "audio":
        if qr_is_mock_mode():
            user_message_text = "[Nota de Voz Simulada] Hola agente, ¿cómo te va?"
        else:
            try:
                # Evolution API descifra el audio automáticamente vía este endpoint
                audio_msg_key = details["message_content"].get("audioMessage", {})
                # Necesitamos el mensaje completo para que Evolution API lo descifre
                full_message_obj = details.get("full_message_obj", {})
                media_payload = {"message": full_message_obj, "convertToMp4": False}
                evo_headers = {
                    "apikey": settings.evolution_api_token,
                    "Content-Type": "application/json",
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    media_res = await client.post(
                        f"{settings.evolution_api_url}/chat/getBase64FromMediaMessage/{agent.whatsapp_qr_instance_name}",
                        headers=evo_headers,
                        json=media_payload,
                    )
                    logger.info(
                        f"[QR AUDIO] Evolution media response: {media_res.status_code} - {media_res.text[:200]}"
                    )
                    if media_res.status_code in [200, 201]:
                        media_data = media_res.json()
                        # La respuesta puede tener 'base64' o 'data' según la versión
                        b64_data = media_data.get("base64") or media_data.get(
                            "data", ""
                        )
                        if b64_data:
                            import base64

                            audio_bytes = base64.b64decode(b64_data)
                            mime_type = audio_msg_key.get(
                                "mimetype", "audio/ogg; codecs=opus"
                            )
                            from services.ai_service import transcribe_audio

                            user_message_text = await transcribe_audio(
                                audio_bytes=audio_bytes,
                                mime_type=mime_type,
                                filename="voice.ogg",
                                stt_provider=agent.stt_provider or "groq_whisper",
                            )
                            logger.info(
                                f"[QR AUDIO] Transcripción exitosa: {user_message_text[:80]}"
                            )
                        else:
                            logger.warning(
                                f"[QR AUDIO] No se obtuvo base64 del media. Respuesta: {media_data}"
                            )
                            user_message_text = "[Nota de Voz - sin transcripción]"
                    else:
                        logger.error(
                            f"[QR AUDIO] Error al obtener media: {media_res.status_code} - {media_res.text}"
                        )
                        user_message_text = "[Nota de Voz - sin transcripción]"
            except Exception as e:
                logger.error(
                    f"Error al transcribir nota de voz QR: {str(e)}", exc_info=True
                )
                token_dec = (
                    decrypt(agent.whatsapp_qr_instance_token)
                    if agent.whatsapp_qr_instance_token
                    else None
                )
                error_detail = f"⚠️ Error audio: {str(e)[:180]}"
                await send_qr_text(
                    instance_name=agent.whatsapp_qr_instance_name,
                    to_phone=phone_number,
                    text=error_detail,
                    token=token_dec,
                )
                return {"status": "error"}

    if not user_message_text.strip() or user_message_text == "[Nota de Voz]":
        return {"status": "ignored"}

    # Responder con IA
    from services.conversation_service import process_conversation_message

    reply = await process_conversation_message(
        db=db,
        agent=agent,
        conversation=conversation,
        user_message_text=user_message_text,
        source_channel="whatsapp",
        whatsapp_message_id=whatsapp_msg_id,
    )

    if not reply or not reply.strip():
        logger.warning(
            "[QR WEBHOOK] IA devolvió respuesta vacía para agente %s, mensaje %s. Enviando fallback.",
            agent.id,
            whatsapp_msg_id,
        )
        reply = "Hola, gracias por tu mensaje. ¿En qué puedo ayudarte?"

    # #region debug report D:reply-generated
    _report_debug_event(
        hypothesis_id="D",
        location="backend/routers/whatsapp.py:_receive_qr_webhook_impl",
        msg="La IA generó respuesta para el mensaje QR",
        data={
            "agent_id": agent.id,
            "conversation_id": conversation.id,
            "reply_length": len(reply or ""),
            "reply_preview": (reply or "")[:120],
        },
    )
    # #endregion

    # Despachar mensaje
    token_decrypted = (
        decrypt(agent.whatsapp_qr_instance_token)
        if agent.whatsapp_qr_instance_token
        else None
    )
    send_success = await send_qr_text(
        instance_name=agent.whatsapp_qr_instance_name,
        to_phone=phone_number,
        text=reply,
        token=token_decrypted,
    )
    # #region debug-point D:send-result
    _report_debug_event(
        hypothesis_id="D",
        location="backend/routers/whatsapp.py:_receive_qr_webhook_impl",
        msg="Resultado del envío de respuesta QR",
        data={
            "agent_id": agent.id,
            "conversation_id": conversation.id,
            "send_success": send_success,
            "instance_name": agent.whatsapp_qr_instance_name,
            "to_phone": phone_number,
        },
    )
    # #endregion
    if not send_success:
        logger.error(
            "[QR SEND ERROR] No se pudo enviar respuesta al teléfono %s para agente %s.",
            phone_number,
            agent.id,
        )
        try:
            import uuid

            debug_conv = (
                db.query(Conversation)
                .filter(Conversation.contact_phone == "PAYLOAD_DEBUG")
                .first()
            )
            if debug_conv:
                debug_msg = DBMessage(
                    id=uuid.uuid4().hex,
                    conversation_id=debug_conv.id,
                    role="assistant",
                    content=(
                        "ERROR QR SEND FAILED: "
                        f"agent={agent.id} phone={phone_number} "
                        f"instance={agent.whatsapp_qr_instance_name}"
                    )[:3000],
                    sent_at=datetime.now(timezone.utc),
                )
                db.add(debug_msg)
                db.commit()
        except Exception as log_err:
            logger.error(
                "[QR SEND ERROR] No se pudo registrar el fallo de envío: %s",
                str(log_err),
            )

    return {"status": "accepted"}


# Helper extractor de Evolution API
def _extract_qr_message_details(data: dict) -> dict | None:
    event = data.get("event")
    # Evolution API envía events del tipo 'messages.upsert' o 'MESSAGES_UPSERT'
    if not event or event.lower() not in ("messages.upsert", "messages_upsert"):
        # #region debug-point A:unexpected-event
        _report_debug_event(
            hypothesis_id="A",
            location="backend/routers/whatsapp.py:_extract_qr_message_details",
            msg="Evento QR descartado por nombre no reconocido",
            data={"event": event},
        )
        # #endregion
        return None

    # Evolution API puede enviar 'data' como lista o como dict
    raw_data = data.get("data", {})
    if isinstance(raw_data, list):
        # Tomar el primer mensaje de la lista que no sea del propio bot
        message_data = None
        for item in raw_data:
            if not item.get("key", {}).get("fromMe", False):
                message_data = item
                break
        if message_data is None:
            return None
    else:
        message_data = raw_data

    key = message_data.get("key", {})
    from_me = key.get("fromMe", False)
    if from_me:
        # #region debug-point C:from-me
        _report_debug_event(
            hypothesis_id="C",
            location="backend/routers/whatsapp.py:_extract_qr_message_details",
            msg="Mensaje QR descartado porque viene marcado como fromMe",
            data={"event": event, "key_id": key.get("id")},
        )
        # #endregion
        return None

    remote_jid = key.get("remoteJid", "")
    if not remote_jid or not (remote_jid.endswith("@s.whatsapp.net") or remote_jid.endswith("@lid")):
        # #region debug-point C:remote-jid-discarded
        _report_debug_event(
            hypothesis_id="C",
            location="backend/routers/whatsapp.py:_extract_qr_message_details",
            msg="Mensaje QR descartado por remoteJid no soportado",
            data={"remote_jid": remote_jid, "key_id": key.get("id")},
        )
        # #endregion
        logger.info(f"[QR EXTRACT] remoteJid descartado: {remote_jid}")
        return None

    # Si es un JID de tipo LID, conservamos el JID completo con sufijo para que Evolution API
    # pueda rutearlo de vuelta adecuadamente sin asumir que es un telefono normal.
    if remote_jid.endswith("@lid"):
        phone_number = remote_jid
    else:
        phone_number = remote_jid.split("@")[0]
    
    whatsapp_msg_id = key.get("id")
    push_name = message_data.get("pushName", "Usuario WhatsApp")

    message_content = message_data.get("message", {})
    if not message_content:
        # #region debug-point C:no-message-content
        _report_debug_event(
            hypothesis_id="C",
            location="backend/routers/whatsapp.py:_extract_qr_message_details",
            msg="Mensaje QR sin message_content",
            data={
                "message_keys": list(message_data.keys())[:15],
                "key_id": key.get("id"),
            },
        )
        # #endregion
        logger.info(
            f"[QR EXTRACT] Sin message_content en message_data: {list(message_data.keys())}"
        )
        return None

    msg_type = "text"
    user_message_text = ""

    if "conversation" in message_content:
        user_message_text = message_content["conversation"]
    elif "extendedTextMessage" in message_content:
        user_message_text = message_content.get("extendedTextMessage", {}).get(
            "text", ""
        )
    elif "audioMessage" in message_content:
        msg_type = "audio"
        user_message_text = "[Nota de Voz]"
    else:
        # #region debug-point C:unsupported-message-type
        _report_debug_event(
            hypothesis_id="C",
            location="backend/routers/whatsapp.py:_extract_qr_message_details",
            msg="Mensaje QR con tipo no reconocido",
            data={
                "message_content_keys": list(message_content.keys())[:15],
                "key_id": key.get("id"),
            },
        )
        # #endregion
        logger.info(
            f"[QR EXTRACT] Tipo de mensaje no reconocido. Claves: {list(message_content.keys())}"
        )

    logger.info(
        f"[QR EXTRACT] Mensaje extraído: phone={phone_number}, type={msg_type}, text_preview={user_message_text[:80]}"
    )
    return {
        "phone_number": phone_number,
        "whatsapp_msg_id": whatsapp_msg_id,
        "push_name": push_name,
        "type": msg_type,
        "text": user_message_text,
        "message_content": message_content,
        "full_message_obj": message_data,
    }
