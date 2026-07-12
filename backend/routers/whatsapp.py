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
    configure_meta_webhook,
)
from services.whatsapp_qr_service import (
    create_qr_instance,
    get_qr_code,
    verify_qr_connection,
    delete_qr_instance,
    delete_qr_instance_safe,
    send_qr_text,
    configure_qr_webhook,
    restart_qr_instance,
    check_evolution_health,
    simulate_qr_scan,
    is_mock_mode as qr_is_mock_mode,
)
from services.whatsapp_waha_service import (
    create_waha_session,
    get_waha_qr,
    verify_waha_connection,
    delete_waha_session,
    send_waha_text,
    send_waha_image,
    restart_waha_session,
    check_waha_health,
    simulate_waha_scan,
    waha_is_mock_mode,
    store_waha_qr,
    _headers,
)
from urllib.parse import urlparse
from services.encryption_service import encrypt, decrypt
from services.ai_service import chat_with_agent
from services.knowledge_service import retrieve_context
from services.lead_service import extract_and_save_lead
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Integration"])


def _get_webhook_base_url(request: "Request") -> str:
    """
    Retorna la URL base correcta para configurar webhooks.
    En Vercel/producción, fuerza HTTPS y usa el header X-Forwarded-Host.
    """
    import os

    env = os.getenv("ENVIRONMENT", "development")

    # En producción Vercel, request.base_url puede ser http://
    # Usar X-Forwarded-Host para obtener el dominio real
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_proto = request.headers.get("x-forwarded-proto", "https")

    if forwarded_host:
        base = f"{forwarded_proto}://{forwarded_host}"
    else:
        base = str(request.base_url).rstrip("/")

    # Forzar HTTPS en producción
    if env == "production" and base.startswith("http://"):
        base = base.replace("http://", "https://", 1)

    return base


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
    request: Request,
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

    # Configurar el webhook en Meta automáticamente para recibir mensajes
    try:
        base_url = _get_webhook_base_url(request)
        webhook_url = f"{base_url}/api/whatsapp/webhook"
        await configure_meta_webhook(
            phone_number_id=body.phone_number_id,
            webhook_url=webhook_url,
            verify_token=body.verify_token,
            access_token=body.access_token,
        )
        logger.info(
            f"Webhook de Meta configurado para agente '{agent.name}' en {webhook_url}"
        )
    except Exception as hook_err:
        logger.warning(
            "No se pudo configurar el webhook de Meta automáticamente para "
            f"'{agent.name}': {hook_err}"
        )

    logger.info(
        f"WhatsApp conectado exitosamente para agente '{agent.name}' "
        f"(phone_number_id={body.phone_number_id}, "
        f"display_name={verification['display_name']})."
    )

    base_url = _get_webhook_base_url(request)
    return {
        "status": "connected",
        "phone_number_id": body.phone_number_id,
        "phone_number": verification.get("phone_number"),
        "display_name": verification.get("display_name"),
        "quality_rating": verification.get("quality_rating"),
        "webhook_url": f"{base_url}/api/whatsapp/webhook",
        "message": f"WhatsApp conectado exitosamente al agente '{agent.name}'. "
        f"Webhook configurado en: {base_url}/api/whatsapp/webhook",
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


@router.post("/{agent_id}/configure-webhook")
async def configure_webhook_meta(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Configura el webhook de Meta Cloud API para recibir eventos de WhatsApp.
    Llama al endpoint de configuración del webhook en Meta Graph API.
    """
    from services.whatsapp_service import configure_meta_webhook

    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    if not agent.whatsapp_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El agente no tiene WhatsApp conectado.",
        )

    if not agent.whatsapp_phone_number_id or not agent.whatsapp_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El agente no tiene phone_number_id o access_token configurados.",
        )

    access_token = decrypt(agent.whatsapp_access_token)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo descifrar el access_token del agente.",
        )

    base_url = str(request.base_url).rstrip("/")
    webhook_url = f"{base_url}/api/whatsapp/webhook"
    verify_token = agent.whatsapp_verify_token or f"genia_verify_{agent_id[:8]}"

    result = await configure_meta_webhook(
        phone_number_id=agent.whatsapp_phone_number_id,
        webhook_url=webhook_url,
        verify_token=verify_token,
        access_token=access_token,
    )

    if result["success"]:
        logger.info(f"Webhook configurado exitosamente para agente '{agent.name}'")
        return {
            "status": "webhook_configured",
            "webhook_url": webhook_url,
            "verify_token": verify_token,
            "message": "Webhook configurado exitosamente. Verifica la configuración en Meta Developers.",
        }
    else:
        logger.error(f"Error configurando webhook: {result['error']}")
        return {
            "status": "webhook_error",
            "error": result["error"],
            "message": f"Error al configurar webhook: {result['error']}",
        }


@router.get("/{agent_id}/qr/debug-state")
async def debug_qr_state(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    ENDPOINT DE DIAGNÓSTICO TEMPORAL (público). Verifica el estado de la
    instancia Evolution usando el token de instancia almacenado (desencriptado
    en runtime). No expone el token en la respuesta.
    """
    from services.whatsapp_qr_service import _candidate_api_keys

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return {"error": "agente no encontrado"}

    instance = agent.whatsapp_qr_instance_name
    token_dec = decrypt(agent.whatsapp_qr_instance_token) if agent.whatsapp_qr_instance_token else None

    result = {
        "instance_name": instance,
        "has_instance_token": bool(token_dec),
        "evolution_url_set": bool(settings.evolution_api_url),
        "evolution_token_set": bool(settings.evolution_api_token),
        "checks": [],
    }

    if not instance or not settings.evolution_api_url:
        result["error"] = "Falta instance_name o evolution_api_url"
        return result

    url = f"{settings.evolution_api_url}/instance/connectionState/{instance}"
    for tk in _candidate_api_keys(token_dec):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, headers={"apikey": tk})
                body = r.text[:500]
                result["checks"].append({
                    "status_code": r.status_code,
                    "body": body,
                })
        except Exception as e:
            result["checks"].append({"exception": str(e)[:300]})

    # Además: info de la instancia
    info_url = f"{settings.evolution_api_url}/instance/info/{instance}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            ri = await client.get(info_url, headers={"apikey": token_dec or settings.evolution_api_token})
            result["instance_info"] = {"status_code": ri.status_code, "body": ri.text[:500]}
    except Exception as e:
        result["instance_info"] = {"exception": str(e)[:300]}

    return result


@router.get("/{agent_id}/status")
async def get_whatsapp_status(
    agent_id: str,
    request: Request,
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
    base_url = _get_webhook_base_url(request)
    if whatsapp_provider == "meta_cloud":
        webhook_url = f"{base_url}/api/whatsapp/webhook"
    elif whatsapp_provider == "waha":
        webhook_url = f"{base_url}/api/whatsapp/webhook/waha/{agent.id}"
    else:
        webhook_url = f"{base_url}/api/whatsapp/webhook/qr/{agent.id}"

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
        "is_mock_mode": qr_is_mock_mode() if whatsapp_provider == "qr_code" else waha_is_mock_mode(),
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
    elif whatsapp_provider == "waha":
        # WAHA Provider
        session_name = agent.whatsapp_qr_instance_name
        if not session_name:
            # Sin session_name en BD → buscar en sesiones activas de WAHA
            from services.whatsapp_waha_service import list_waha_sessions
            try:
                sessions = await list_waha_sessions()
                prefix = f"genia_{agent.id[:8]}"
                for s in sessions:
                    n = s.get("name", "")
                    st = s.get("status", "").upper()
                    if n.startswith(prefix) and st == "WORKING":
                        session_name = n
                        agent.whatsapp_qr_instance_name = n
                        agent.whatsapp_qr_connected = True
                        result["connected"] = True
                        result["whatsapp_qr_connected"] = True
                        me = s.get("me") or {}
                        result["phone_number"] = str(me.get("id", "")).split("@")[0]
                        result["display_name"] = me.get("pushName")
                        db.commit()
                        break
            except Exception:
                pass

        if session_name:
            verification = await verify_waha_connection(session_name)
            result["connected"] = verification["connected"]
            result["whatsapp_qr_connected"] = verification["connected"]
            result["phone_number"] = verification.get("phone_number")
            result["display_name"] = verification.get("display_name")
            result["error"] = verification.get("error")

            if not verification["connected"]:
                persisted = getattr(agent, "whatsapp_qr_code", None)
                result["qr_code"] = persisted or await get_waha_qr(session_name)
            else:
                result["qr_code"] = None

            if agent.whatsapp_qr_connected != verification["connected"]:
                agent.whatsapp_qr_connected = verification["connected"]
                db.commit()
        else:
            result["connected"] = False
            result["whatsapp_qr_connected"] = False
    else:
        # QR Code Provider (Evolution API)
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

                if not reply or not reply.strip():
                    logger.warning(
                        "[META WEBHOOK] IA devolvió respuesta vacía para agente %s, "
                        "mensaje %s. Enviando fallback.",
                        agent.id,
                        whatsapp_msg_id,
                    )
                    reply = "Hola, gracias por tu mensaje. ¿En qué puedo ayudarte?"

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

    if body.provider not in ["meta_cloud", "qr_code", "waha"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proveedor no válido. Debe ser 'meta_cloud', 'qr_code' o 'waha'.",
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

    # Eliminar instancia previa si existe para evitar acumular sesiones huérfanas
    if agent.whatsapp_qr_instance_name:
        logger.info(f"Eliminando instancia previa '{agent.whatsapp_qr_instance_name}' antes de crear nueva.")
        await delete_qr_instance_safe(agent.whatsapp_qr_instance_name)

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
    base_url = _get_webhook_base_url(request)
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


@router.post("/{agent_id}/qr/restart")
async def restart_whatsapp_qr(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Fuerza el reinicio de la instancia de WhatsApp QR para obtener un nuevo
    código QR limpio si el dispositivo se desconectó.
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

    if not agent.whatsapp_qr_instance_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El agente no tiene una instancia QR activa.",
        )

    qr_code = await restart_qr_instance(agent.whatsapp_qr_instance_name)
    if not qr_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo obtener un nuevo código QR tras reiniciar la instancia.",
        )

    agent.whatsapp_qr_connected = False
    db.commit()

    return {
        "status": "connecting",
        "instance_name": agent.whatsapp_qr_instance_name,
        "qr_code": qr_code,
        "message": "Instancia reiniciada. Por favor, escanea el nuevo código QR.",
    }


@router.get("/{agent_id}/qr/health")
async def health_whatsapp_qr(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Verifica el estado del servidor de la Evolution API de forma rápida.
    """
    status_health = await check_evolution_health()
    return status_health


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


# ---------------------------------------------------------------------------
# Integración WAHA (Código QR, open-source)
# ---------------------------------------------------------------------------


@router.post("/{agent_id}/waha/connect")
async def connect_whatsapp_waha(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Inicializa una sesión WAHA (WhatsApp HTTP API) para vincular el agente
    mediante código QR. Crea la sesión, configura el webhook y retorna el QR.
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

    import time

    # Eliminar sesión previa si existe para evitar acumular sesiones huérfanas
    if agent.whatsapp_qr_instance_name:
        logger.info(f"Eliminando sesión WAHA previa '{agent.whatsapp_qr_instance_name}'.")
        await delete_waha_session(agent.whatsapp_qr_instance_name)

    session_name = f"genia_{agent.id[:8]}_{int(time.time())}"
    agent.whatsapp_qr_instance_name = session_name

    # Webhook apuntando al host actual
    base_url = _get_webhook_base_url(request)
    webhook_url = f"{base_url}/api/whatsapp/webhook/waha/{agent.id}"

    init_res = await create_waha_session(session_name, webhook_url)
    if init_res.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear la sesión WAHA: {init_res.get('error')}",
        )

    qr_code = init_res.get("qr")

    # Si WAHA no devolvió el QR en la respuesta, esperar hasta 10s
    # consultando la BD (webhook) y REST endpoint correcto.
    if not qr_code:
        import asyncio
        for attempt in range(10):
            await asyncio.sleep(1)
            # 1. Ver si el webhook ya guardó el QR en BD
            db.refresh(agent)
            if agent.whatsapp_qr_code:
                qr_code = agent.whatsapp_qr_code
                logger.info(f"QR recibido vía webhook WAHA tras {attempt + 1}s.")
                break
            # 2. Intentar REST directo con endpoint correcto
            rest_qr = await get_waha_qr(session_name)
            if rest_qr:
                qr_code = rest_qr
                logger.info(f"QR obtenido vía REST WAHA tras {attempt + 1}s.")
                break

    # Persistir QR en BD para que el status endpoint lo encuentre
    if qr_code:
        agent.whatsapp_qr_code = qr_code
        store_waha_qr(session_name, qr_code)

    agent.whatsapp_provider = "waha"
    channels = agent.channels or []
    if "whatsapp" not in channels:
        agent.channels = channels + ["whatsapp"]

    db.commit()

    return {
        "status": "connecting",
        "session_name": session_name,
        "qr_code": qr_code,
        "message": "Escanea el código QR desde tu celular en WhatsApp > Dispositivos Vinculados.",
    }


@router.post("/{agent_id}/waha/disconnect")
async def disconnect_whatsapp_waha(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Desconecta la línea WAHA y destruye la sesión."""
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
        await delete_waha_session(agent.whatsapp_qr_instance_name)

    agent.whatsapp_qr_instance_name = None
    agent.whatsapp_qr_connected = False
    db.commit()

    logger.info(f"WhatsApp WAHA desconectado para agente '{agent.name}'.")
    return {
        "status": "disconnected",
        "message": f"WhatsApp WAHA desconectado del agente '{agent.name}'.",
    }


@router.post("/{agent_id}/waha/restart")
async def restart_whatsapp_waha(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Reinicia la sesión WAHA para obtener un nuevo QR limpio."""
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    if not agent.whatsapp_qr_instance_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El agente no tiene una sesión WAHA activa.",
        )

    base_url = _get_webhook_base_url(request)
    webhook_url = f"{base_url}/api/whatsapp/webhook/waha/{agent.id}"
    qr_code = await restart_waha_session(agent.whatsapp_qr_instance_name, webhook_url)
    if not qr_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo obtener un nuevo código QR tras reiniciar la sesión WAHA.",
        )

    agent.whatsapp_qr_code = qr_code
    agent.whatsapp_qr_connected = False
    db.commit()

    return {
        "status": "connecting",
        "session_name": agent.whatsapp_qr_instance_name,
        "qr_code": qr_code,
        "message": "Sesión WAHA reiniciada. Por favor, escanea el nuevo código QR.",
    }


@router.get("/{agent_id}/waha/health")
async def health_whatsapp_waha():
    """Verifica el estado del servidor WAHA."""
    return await check_waha_health()


@router.post("/{agent_id}/waha/sync")
async def sync_whatsapp_waha(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Sincroniza el estado de la BD con las sesiones activas de WAHA.
    Útil cuando WAHA CORE no envía webhooks y la sesión se conectó
    sin que el backend lo sepa.
    """
    from services.whatsapp_waha_service import list_waha_sessions

    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    sessions = await list_waha_sessions()
    # Buscar sesiones cuyo nombre contenga el agent_id (ej: genia_547c07f7_...)
    agent_prefix = f"genia_{agent.id[:8]}"
    for s in sessions:
        name = s.get("name", "")
        status = s.get("status", "").upper()
        me = s.get("me") or {}
        if name.startswith(agent_prefix) and status == "WORKING" and me.get("id"):
            agent.whatsapp_qr_instance_name = name
            agent.whatsapp_qr_connected = True
            agent.whatsapp_qr_code = None
            db.commit()
            return {
                "status": "synced",
                "connected": True,
                "session_name": name,
                "phone_number": str(me.get("id", "")).split("@")[0],
                "display_name": me.get("pushName"),
                "message": "Sesión WAHA sincronizada exitosamente.",
            }

    # Si llegamos aquí, no se encontró sesión WORKING
    if agent.whatsapp_qr_instance_name:
        # Verificar la sesión actual
        v = await verify_waha_connection(agent.whatsapp_qr_instance_name)
        if v["connected"]:
            agent.whatsapp_qr_connected = True
            db.commit()
            return {
                "status": "synced",
                "connected": True,
                "session_name": agent.whatsapp_qr_instance_name,
                "phone_number": v.get("phone_number"),
                "display_name": v.get("display_name"),
                "message": "Sesión WAHA verificada y conectada.",
            }

    return {
        "status": "not_found",
        "connected": False,
        "message": "No se encontró ninguna sesión WAHA conectada para este agente. Genera un nuevo código QR.",
    }


@router.post("/{agent_id}/waha/simulate-scan")
async def simulate_scan_waha(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Utilidad de pruebas (modo desarrollo): simula el escaneo del QR WAHA."""
    if not waha_is_mock_mode():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La simulación solo está disponible en modo desarrollo local sin WAHA.",
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

    session_name = agent.whatsapp_qr_instance_name or f"genia_agent_{agent.id}"
    simulate_waha_scan(session_name)
    agent.whatsapp_qr_connected = True
    db.commit()

    logger.info(f"[SIMULACIÓN WAHA] QR escaneado para agente '{agent.name}'.")
    return {
        "status": "connected",
        "message": f"Línea WAHA simulada y conectada para el agente '{agent.name}'.",
    }


@router.post("/webhook/waha/{agent_id}")
async def receive_waha_webhook(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Webhook para recibir eventos de WAHA (mensajes, qr, session.status).
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload JSON no válido.",
        )

    logger.info(
        f"[WAHA WEBHOOK] Recibido para agent_id={agent_id}, event={data.get('event')}"
    )

    try:
        return await _receive_waha_webhook_impl(agent_id, db, data)
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.error(f"[WAHA WEBHOOK ERROR] Agent {agent_id}: {err_msg}")
        return {"status": "accepted", "warning": f"Error interno procesado: {str(e)[:200]}"}


async def _receive_waha_webhook_impl(agent_id: str, db: Session, data: dict):
    logger.info(
        f"[WAHA WEBHOOK IMPL] event={data.get('event')}, type={data.get('payload', {}).get('type')}, keys={list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
    )

    agent = (
        db.query(Agent).filter(Agent.id == agent_id, Agent.status == "active").first()
    )
    if not agent:
        logger.warning(f"Webhook WAHA para agente inexistente/inactivo: {agent_id}")
        return {"status": "ignored"}

    event = str(data.get("event", "")).lower()
    payload = data.get("payload", {}) or {}

    # Eventos administrativos
    if event in ("session.status", "session_status"):
        state = (payload.get("state") or "").upper()
        if state == "CONNECTED":
            agent.whatsapp_qr_connected = True
            db.commit()
            logger.info(f"Línea WAHA de '{agent.name}' marcada CONECTADA.")
        elif state in ("DISCONNECTED", "SCAN_QR", "STARTING", "QRISREADY"):
            if state != "SCAN_QR":
                agent.whatsapp_qr_connected = False
                db.commit()
            logger.info(f"Línea WAHA de '{agent.name}' estado={state}.")
        elif state == "FAILED":
            agent.whatsapp_qr_connected = False
            db.commit()
            logger.warning(f"Línea WAHA de '{agent.name}' FALLÓ: {payload.get('reason')}")
        return {"status": "accepted"}

    if event == "qr":
        # WAHA 2024+ entrega el QR solo por webhook; lo guardamos para el frontend.
        qr_data = payload.get("qr") if isinstance(payload, dict) else None
        if not qr_data and isinstance(payload, str):
            qr_data = payload
        if qr_data:
            store_waha_qr(agent.whatsapp_qr_instance_name or "", qr_data)
            # Persistir en BD (si la migración está aplicada) para sobrevivir
            # en serverless; si la columna no existe aún, se ignora sin fallar.
            try:
                agent.whatsapp_qr_code = qr_data
                db.add(agent)
                db.commit()
            except Exception:
                db.rollback()
            logger.info(f"Código QR WAHA capturado para '{agent.name}'.")
        else:
            logger.info(f"Evento QR WAHA sin datos para '{agent.name}'.")
        return {"status": "accepted"}

    if event != "message":
        logger.info(f"[WAHA] Evento no manejado: {event}")
        return {"status": "accepted"}

    # Mensaje entrante
    if payload.get("fromMe"):
        return {"status": "ignored"}

    phone_number = payload.get("from") or payload.get("chatId") or ""
    if not phone_number:
        logger.info("[WAHA EXTRACT] Sin 'from'/'chatId'. Ignorando.")
        return {"status": "ignored"}

    whatsapp_msg_id = payload.get("id")
    msg_type = payload.get("type", "chat")
    push_name = (payload.get("sender") or {}).get("pushName", "Usuario WhatsApp")
    user_message_text = payload.get("body", "")

    # Deduplicar
    from models.conversation import Message as DBMessage

    exists = (
        db.query(DBMessage)
        .filter(DBMessage.whatsapp_message_id == whatsapp_msg_id)
        .first()
    )
    if exists:
        logger.info(f"Mensaje WAHA {whatsapp_msg_id} ya procesado. Ignorando.")
        return {"status": "ignored"}

    # Obtener/crear conversación (phone_number conserva el chatId p.ej. 57..@c.us)
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
        if user_message_text and user_message_text.strip().lower() in [
            "hola", "reiniciar", "reinicia", "iniciar",
        ]:
            should_reactivate = True
        if should_reactivate:
            conversation.status = "active"
            db.commit()
        else:
            logger.info(f"Conversación WAHA {conversation.id} en handoff. Ignorando IA.")
            return {"status": "ignored"}

    # DIAG: save payload type info in DB for voice notes
    if msg_type in ("ptt", "audio"):
        try:
            diag = DBMessage(
                conversation_id=conversation.id,
                role="system",
                content=f"[DIAG] voice note received. media={bool(payload.get('media'))}, base64={bool(payload.get('base64'))}, body='{payload.get('body', '')[:50]}', mime={payload.get('mimetype')}",
                whatsapp_message_id=f"diag_{whatsapp_msg_id}",
            )
            db.add(diag)
            db.commit()
        except Exception:
            db.rollback()

    # Nota de voz (ptt/audio) — descargar y transcribir
    if msg_type in ("ptt", "audio") and not waha_is_mock_mode():
        try:
            media_url = payload.get("media") or ""
            audio_bytes = None
            mime_type = payload.get("mimetype") or "audio/ogg; codecs=opus"
            if payload.get("base64"):
                import base64
                audio_bytes = base64.b64decode(payload["base64"])
            elif media_url and media_url.startswith("http"):
                parsed = urlparse(media_url)
                if parsed.hostname in ("localhost", "127.0.0.1"):
                    download_url = settings.waha_api_url.rstrip("/") + parsed.path
                else:
                    download_url = media_url
                async with httpx.AsyncClient(timeout=30.0) as client:
                    dl = await client.get(download_url, headers=_headers())
                    if dl.status_code == 200:
                        audio_bytes = dl.content
            if audio_bytes:
                from services.ai_service import transcribe_audio
                user_message_text = await transcribe_audio(
                    audio_bytes=audio_bytes,
                    mime_type=mime_type,
                    filename="voice.ogg",
                    stt_provider=agent.stt_provider or "groq_whisper",
                )
                logger.info(f"[WAHA AUDIO] Transcripción: {user_message_text[:80]}")
            else:
                # WAHA CORE no sirve archivos de audio — responder directamente
                reply = "He recibido tu nota de voz. Por el momento no puedo procesar audios, ¿podrías escribirme en texto?"
                send_success = await send_waha_text(
                    session_name=agent.whatsapp_qr_instance_name,
                    to_phone=phone_number,
                    text=reply,
                )
                if not send_success:
                    logger.error("[WAHA AUDIO FALLBACK] Error enviando respuesta para %s", phone_number)
                return {"status": "accepted", "note": "audio_no_transcription"}
        except Exception as e:
            logger.error(f"Error transcribiendo nota de voz WAHA: {str(e)}", exc_info=True)
            reply = "He recibido tu nota de voz pero no pude procesarla. ¿Podrías escribirme en texto?"
            await send_waha_text(
                session_name=agent.whatsapp_qr_instance_name,
                to_phone=phone_number,
                text=reply,
            )
            return {"status": "accepted", "note": "audio_error"}

    if not user_message_text or not user_message_text.strip():
        return {"status": "ignored"}

    # Responder con IA
    try:
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
            logger.warning("[WAHA WEBHOOK] IA devolvió respuesta vacía. Enviando fallback.")
            reply = "Hola, gracias por tu mensaje. ¿En qué puedo ayudarte?"
    except Exception as e:
        logger.error(f"[WAHA WEBHOOK] Error en process_conversation_message: {str(e)}", exc_info=True)
        reply = "Ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo."

    send_success = await send_waha_text(
        session_name=agent.whatsapp_qr_instance_name,
        to_phone=phone_number,
        text=reply,
    )

    if not send_success:
        logger.error(
            "[WAHA SEND ERROR] No se pudo enviar respuesta a %s para agente %s.",
            phone_number,
            agent.id,
        )

    return {"status": "accepted"}


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

    logger.info(
        f"[QR WEBHOOK] Recibido para agent_id={agent_id}, event={data.get('event')}"
    )

    try:
        return await _receive_qr_webhook_impl(agent_id, request, db, data)
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger.error(f"[QR WEBHOOK ERROR] Agent {agent_id}: {err_msg}")
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
    logger.info(
        f"[QR WEBHOOK IMPL] Iniciado: event={data.get('event')}, keys={list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
    )

    agent = (
        db.query(Agent).filter(Agent.id == agent_id, Agent.status == "active").first()
    )
    if not agent:
        logger.warning(
            f"Webhook QR recibido para agente inexistente o inactivo: {agent_id}"
        )
        return {"status": "ignored"}

    # Extraer detalles
    details = _extract_qr_message_details(data, agent)
    if not details:
        # Evento administrativo o no-mensaje
        event_type = str(data.get("event", "")).lower()
        if event_type in ("connection.update", "connection_update"):
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
        elif event_type in ("qrcode.updated", "qrcode_updated"):
            logger.info(f"Código QR actualizado para el agente '{agent.name}'.")
        return {"status": "accepted"}

    phone_number = details["phone_number"]
    whatsapp_msg_id = details["whatsapp_msg_id"]
    user_message_text = details["text"]
    msg_type = details["type"]
    push_name = details["push_name"]

    # Deduplicar
    from models.conversation import Message as DBMessage

    exists = (
        db.query(DBMessage)
        .filter(DBMessage.whatsapp_message_id == whatsapp_msg_id)
        .first()
    )
    if exists:
        logger.info(f"Mensaje {whatsapp_msg_id} ya procesado. Ignorando.")
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
                        f"[QR AUDIO] Evolution media response: {media_res.status_code}"
                    )
                    if media_res.status_code in [200, 201]:
                        media_data = media_res.json()
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
                            f"[QR AUDIO] Error al obtener media: {media_res.status_code} - {media_res.text[:200]}"
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

    if not send_success:
        logger.error(
            "[QR SEND ERROR] No se pudo enviar respuesta al teléfono %s para agente %s.",
            phone_number,
            agent.id,
        )

    return {"status": "accepted"}


# Helper extractor de Evolution API
def _extract_qr_message_details(data: dict, agent: Agent) -> dict | None:
    event = data.get("event")
    # Evolution API envía events del tipo 'messages.upsert' o 'MESSAGES_UPSERT'
    if not event or event.lower() not in ("messages.upsert", "messages_upsert"):
        return None

    # Evolution API v2 puede anidar el mensaje de varias formas.
    # Normalizamos para obtener siempre el objeto mensaje (con 'key'/'message').
    raw_data = data.get("data", {})

    # Caso 1: data es una lista de mensajes
    if isinstance(raw_data, list):
        message_data = None
        for item in raw_data:
            if isinstance(item, dict) and not item.get("key", {}).get("fromMe", False):
                message_data = item
                break
        if message_data is None:
            return None
    # Caso 2: data es un dict que envuelve otro 'data' con el mensaje (v2)
    elif isinstance(raw_data, dict):
        inner = raw_data.get("data")
        if isinstance(inner, dict) and ("key" in inner or "message" in inner):
            message_data = inner
        elif isinstance(inner, list) and inner:
            message_data = next(
                (i for i in inner if isinstance(i, dict) and not i.get("key", {}).get("fromMe", False)),
                inner[0],
            )
        else:
            message_data = raw_data
    else:
        return None

    if not isinstance(message_data, dict):
        return None

    key = message_data.get("key", {})
    from_me = key.get("fromMe", False)
    if from_me:
        return None

    # Filtrar recibos de entrega/lectura: no son mensajes nuevos del usuario
    msg_status = key.get("status", "")
    if msg_status in ("DELIVERY_ACK", "READ", "READ_SELF", "PLAYED"):
        logger.info(
            f"[QR EXTRACT] Descartando receipt status={msg_status} para msg_id={key.get('id')}"
        )
        return None

    remote_jid = key.get("remoteJid", "")
    if not remote_jid or not (
        remote_jid.endswith("@s.whatsapp.net") or remote_jid.endswith("@lid")
    ):
        logger.info(f"[QR EXTRACT] remoteJid descartado: {remote_jid}")
        return None

    # Normalizar: extraer solo la parte numérica (sin @lid ni @s.whatsapp.net)
    # para que el lookup de conversaciones funcione siempre con el mismo formato.
    phone_number = remote_jid.split("@")[0]

    whatsapp_msg_id = key.get("id")
    push_name = message_data.get("pushName", "Usuario WhatsApp")

    message_content = message_data.get("message", {}) or {}
    if not message_content:
        logger.info(
            f"[QR EXTRACT] Sin message_content o vacío en message_data: {list(message_data.keys())}"
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
        logger.info(
            f"[QR EXTRACT] Tipo de mensaje no reconocido. Claves: {list(message_content.keys())}"
        )

    logger.info(
        f"[QR EXTRACT] Mensaje extraído: phone={phone_number}, type={msg_type}, text_preview=({len(user_message_text or '')} chars)"
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
