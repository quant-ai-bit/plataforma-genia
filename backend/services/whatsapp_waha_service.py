"""
Servicio para interactuar con WAHA (WhatsApp HTTP API) - integración vía Código QR.

WAHA es una API open-source basada en whatsapp-web.js / Baileys. Expone:
  - POST /api/sessions/start   -> crea sesión y (con waitForScan) retorna el QR
  - GET  /api/{session}/qr     -> obtiene el QR en base64
  - POST /api/sendText         -> envía texto
  - POST /api/sendImage        -> envía imagen
  - GET  /api/sessions/{name}  -> estado de la sesión
  - DELETE /api/sessions/{name}-> elimina la sesión
  - POST /api/{session}/logout -> cierra sesión (mantiene sesión)

Incluye un modo de simulación (Mock) si no se configura WAHA_API_URL, para
permitir probar el flujo de escaneo en desarrollo local.

Características para soporte multi-agente (10+ sesiones simultáneas):
  - Monitoreo de sesiones con reconexión automática
  - Detección de sesiones caídas y limpieza automática
  - Prevención de bloqueos por spam con delays inteligentes
  - Optimización de recursos para múltiples sesiones
"""

import logging
import httpx
import asyncio
import time
from datetime import datetime, timezone, timedelta
from config import settings

logger = logging.getLogger(__name__)

# Diccionario en memoria para simular sesiones WAHA en desarrollo local
mock_sessions = {}

# Caché del último QR entregado por el evento webhook 'qr' (WAHA 2024+ solo
# entrega el QR vía webhook, no por REST). Clave: session_name -> qr base64.
waha_qr_cache: dict[str, str] = {}

# Monitoreo de sesiones para multi-agente
session_health: dict[str, dict] = {}  # session_name -> {last_check, status, error_count}
SESSION_CHECK_INTERVAL = 60  # segundos entre verificaciones de salud
MAX_ERROR_COUNT = 5  # errores consecutivos antes de marcar sesión como caída
SESSION_STALE_HOURS = 24  # horas sin actividad antes de limpiar sesión huérfana
MAX_RESTART_ATTEMPTS = 3  # intentos máximos de restart antes de pedir QR nuevo


async def restart_waha_session_by_name(session_name: str) -> bool:
    """
    Intenta reiniciar una sesión WAHA existente usando las cookies persistidas
    en el volumen Docker. NO requiere escanear QR nuevamente si las cookies
    siguen válidas.
    
    Retorna True si el restart fue exitoso, False si requiere QR nuevo.
    """
    if waha_is_mock_mode():
        return False

    url = f"{settings.waha_api_url}/api/sessions/{session_name}/start"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=_headers())
            if response.status_code in [200, 201]:
                data = response.json()
                status = (data.get("status") or "").upper()
                logger.info(f"[RESTART SESSION] Sesión '{session_name}' reiniciada. Estado: {status}")
                # Esperar breve para que WAHA intente reconectar con cookies
                await asyncio.sleep(3)
                # Verificar si realmente se conectó
                verification = await verify_waha_connection(session_name)
                if verification.get("connected"):
                    logger.info(f"[RESTART SESSION] ✅ Sesión '{session_name}' reconectada exitosamente con cookies.")
                    return True
                else:
                    logger.warning(f"[RESTART SESSION] Sesión '{session_name}' reiniciada pero no conectada aún. Estado actual: {verification}")
                    # Dar un poco más de tiempo y re-verificar
                    await asyncio.sleep(5)
                    verification2 = await verify_waha_connection(session_name)
                    if verification2.get("connected"):
                        logger.info(f"[RESTART SESSION] ✅ Sesión '{session_name}' reconectada tras segundo intento.")
                        return True
                    return False
            elif response.status_code == 404:
                logger.warning(f"[RESTART SESSION] Sesión '{session_name}' no encontrada en WAHA. Se requiere QR nuevo.")
                return False
            else:
                logger.warning(f"[RESTART SESSION] Error reiniciando '{session_name}': {response.status_code} - {response.text[:200]}")
                return False
    except Exception as e:
        logger.error(f"[RESTART SESSION] Excepción reiniciando '{session_name}': {e}")
        return False


def store_waha_qr(session_name: str, qr: str) -> None:
    """Guarda el QR más reciente recibido por webhook para servirlo al frontend."""
    if session_name and qr:
        waha_qr_cache[session_name] = qr


def get_cached_waha_qr(session_name: str) -> str | None:
    """Recupera el último QR conocido desde la caché de webhook."""
    return waha_qr_cache.get(session_name)


def update_session_health(session_name: str, status: str, error: str = None) -> None:
    """Actualiza el estado de salud de una sesión para monitoreo."""
    if session_name not in session_health:
        session_health[session_name] = {
            "last_check": datetime.now(timezone.utc),
            "status": "unknown",
            "error_count": 0,
            "last_error": None,
            "created_at": datetime.now(timezone.utc),
        }
    
    health = session_health[session_name]
    health["last_check"] = datetime.now(timezone.utc)
    health["status"] = status
    
    if error:
        health["error_count"] += 1
        health["last_error"] = error
    else:
        health["error_count"] = 0
        health["last_error"] = None


def is_session_healthy(session_name: str) -> bool:
    """Verifica si una sesión está saludable basado en el monitoreo."""
    if session_name not in session_health:
        return True  # Si no hay datos, asumir saludable
    
    health = session_health[session_name]
    
    # Si tiene muchos errores consecutivos, considerar no saludable
    if health["error_count"] >= MAX_ERROR_COUNT:
        return False
    
    # Si el último check fue hace mucho tiempo, considerar potencialmente no saludable
    last_check = health["last_check"]
    if datetime.now(timezone.utc) - last_check > timedelta(hours=1):
        return False
    
    return True


async def cleanup_stale_sessions() -> dict:
    """
    Limpia sesiones huérfanas o caídas del servidor WAHA.
    Útil para mantener estabilidad con múltiples sesiones.
    """
    if waha_is_mock_mode():
        return {"cleaned": 0, "message": "Modo mock, no hay sesiones que limpiar"}
    
    try:
        sessions = await list_waha_sessions()
        cleaned = 0
        results = []
        
        for session in sessions:
            name = session.get("name", "")
            status = session.get("status", "").upper()
            
            # Verificar si la sesión está en estado fallido
            if status in ("FAILED", "DISCONNECTED", "ERROR"):
                logger.info(f"[CLEANUP] Eliminando sesión caída: {name} (status={status})")
                await delete_waha_session(name)
                cleaned += 1
                results.append({"session": name, "action": "deleted", "reason": f"status={status}"})
                continue
            
            # Verificar sesiones muy antiguas (más de 24 horas sin actividad)
            if name in session_health:
                health = session_health[name]
                created_at = health.get("created_at")
                if created_at and datetime.now(timezone.utc) - created_at > timedelta(hours=SESSION_STALE_HOURS):
                    # Verificar si realmente está conectada
                    verification = await verify_waha_connection(name)
                    if not verification.get("connected"):
                        logger.info(f"[CLEANUP] Eliminando sesión antigua no conectada: {name}")
                        await delete_waha_session(name)
                        cleaned += 1
                        results.append({"session": name, "action": "deleted", "reason": "stale_and_disconnected"})
        
        return {
            "cleaned": cleaned,
            "total_sessions": len(sessions),
            "details": results,
            "message": f"Se limpiaron {cleaned} sesiones de {len(sessions)} totales"
        }
    except Exception as e:
        logger.error(f"Error en cleanup_stale_sessions: {str(e)}")
        return {"cleaned": 0, "error": str(e)}


async def monitor_all_sessions() -> dict:
    """
    Monitorea todas las sesiones activas y reporta estado.
    Ejecutar periódicamente para mantener estabilidad.
    """
    if waha_is_mock_mode():
        return {"healthy": len(mock_sessions), "unhealthy": 0, "mode": "mock"}
    
    try:
        sessions = await list_waha_sessions()
        healthy = 0
        unhealthy = 0
        details = []
        
        for session in sessions:
            name = session.get("name", "")
            status = session.get("status", "").upper()
            
            # Verificar salud de cada sesión
            verification = await verify_waha_connection(name)
            is_healthy = verification.get("connected", False)
            
            if is_healthy:
                healthy += 1
                update_session_health(name, "healthy")
                details.append({"session": name, "status": "healthy", "phone": verification.get("phone_number")})
            else:
                unhealthy += 1
                update_session_health(name, "unhealthy", verification.get("error"))
                details.append({"session": name, "status": "unhealthy", "error": verification.get("error")})
                
                # Intentar reconexión automática si es posible
                if status in ("DISCONNECTED", "FAILED"):
                    logger.warning(f"[MONITOR] Sesión {name} caída. Intentando limpieza automática.")
                    await delete_waha_session(name)
        
        return {
            "healthy": healthy,
            "unhealthy": unhealthy,
            "total": len(sessions),
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error en monitor_all_sessions: {str(e)}")
        return {"healthy": 0, "unhealthy": 0, "error": str(e)}


async def get_multi_session_stats() -> dict:
    """Obtiene estadísticas del sistema multi-sesión para diagnóstico."""
    if waha_is_mock_mode():
        return {"mode": "mock", "sessions": len(mock_sessions)}
    
    try:
        sessions = await list_waha_sessions()
        active_sessions = []
        total_agents = 0
        
        for session in sessions:
            name = session.get("name", "")
            status = session.get("status", "").upper()
            me = session.get("me") or {}
            
            if status in ("WORKING", "CONNECTED"):
                active_sessions.append({
                    "name": name,
                    "status": status,
                    "phone": str(me.get("id", "")).split("@")[0],
                    "display_name": me.get("pushName"),
                    "health": session_health.get(name, {}).get("status", "unknown")
                })
                total_agents += 1
        
        return {
            "mode": "production",
            "total_sessions": len(sessions),
            "active_sessions": total_agents,
            "sessions": active_sessions,
            "server_url": settings.waha_api_url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"mode": "production", "error": str(e)}

MOCK_QR_BASE64 = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJQAAACUAQMAAABvMD4ZAAAAA1BMVEUAAACnej3aAAAA"
    "AXRSTlMAQObYZgAAAAlwSFlzAAAOxAAADsQBlbZJywAAABpJREFUeNpiYGBgYGBgYGBgYGBgYGBgYGBgYADADAADwAB"
    "g4m4AAAAASUVORK5CYII="
)


def waha_is_mock_mode() -> bool:
    """Retorna True si no está configurada la URL de WAHA."""
    return not settings.waha_api_url


async def verify_session_exists(session_name: str) -> bool:
    """Verifica si una sesión existe en WAHA (sin importar su estado)."""
    if waha_is_mock_mode():
        return session_name in mock_sessions

    url = f"{settings.waha_api_url}/api/sessions/{session_name}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=_headers())
            return r.status_code == 200
    except Exception as e:
        logger.warning(f"[VERIFY SESSION] Excepción al verificar sesión '{session_name}': {e}")
        return False


async def ensure_session_active(agent, webhook_url: str, db_session=None) -> tuple[bool, str | None]:
    """
    Verifica que la sesión WAHA del agente exista en el servidor.
    Si no existe, intenta auto-recuperarla (genera nuevo QR).
    Retorna (success, session_name_actualizado)
    """
    session_name = getattr(agent, "whatsapp_qr_instance_name", None)

    if session_name:
        exists = await verify_session_exists(session_name)
        if exists:
            return True, session_name

        logger.warning(f"[ENSURE SESSION] Sesión '{session_name}' no existe en WAHA. Intentando auto-recuperación...")

    result = await auto_recover_waha_session(agent, webhook_url, db_session=db_session)
    if result.get("recovered"):
        new_name = result.get("session_name")
        logger.info(f"[ENSURE SESSION] Sesión recuperada: '{new_name}' (action={result.get('action')})")
        return True, new_name

    logger.error(f"[ENSURE SESSION] No se pudo recuperar sesión para agente {agent.id}: {result.get('error')}")
    return False, getattr(agent, "whatsapp_qr_instance_name", None)


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if settings.waha_api_key:
        headers["X-Api-Key"] = settings.waha_api_key
    return headers


def _normalize_chat_id(phone: str) -> str:
    """WAHA usa chatId con sufijo (@c.us para números, @lid para business, @g.us grupos)."""
    if "@" in phone:
        return phone
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"{digits}@c.us"


async def list_waha_sessions() -> list[dict]:
    """Lista todas las sesiones WAHA."""
    if waha_is_mock_mode():
        return list(mock_sessions.values())

    url = f"{settings.waha_api_url}/api/sessions"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=_headers())
            if r.status_code in [200, 201]:
                return r.json()
            return []
    except Exception as e:
        logger.error(f"Excepción al listar sesiones WAHA: {str(e)}")
        return []


async def create_waha_session(session_name: str, webhook_url: str, history_sync: bool = False) -> dict:
    """
    Crea (o reutiliza) una sesión en WAHA y retorna el QR inicial.
    Si history_sync=True, habilita el store de NOWEB para poder recuperar
    el historial de chats después de la conexión.
    """
    if waha_is_mock_mode():
        logger.info(f"[MOCK WAHA] Creando sesión simulada: '{session_name}'")
        mock_sessions[session_name] = {
            "status": "SCAN_QR",
            "qr": MOCK_QR_BASE64,
            "phone": None,
            "display_name": None,
        }
        return {"status": "created", "session": session_name, "qr": MOCK_QR_BASE64}

    url = f"{settings.waha_api_url}/api/sessions"
    payload = {
        "name": session_name,
        "start": True,
        "config": {
            "webhooks": [{
                "url": webhook_url,
                "events": ["message", "session.status"],
            }],
        },
    }
    if history_sync:
        payload["config"]["noweb"] = {
            "store": {
                "enabled": True,
                "fullSync": True,
            }
        }
        logger.info(f"[WAHA] Store NOWEB habilitado para sesión '{session_name}' (fullSync=True).")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=_headers(), json=payload)
            if response.status_code in [200, 201]:
                data = response.json()
                qr = data.get("qr") or (data.get("qrcode") or "")
                if qr:
                    store_waha_qr(session_name, qr)
                logger.info(f"Sesión WAHA '{session_name}' creada.")
                return {"status": "created", "session": session_name, "qr": qr}
            elif response.status_code == 409:
                # Ya existe -> obtener QR existente
                logger.warning(f"Sesión WAHA '{session_name}' ya existe. Reutilizando.")
                qr = await get_waha_qr(session_name)
                return {"status": "created", "session": session_name, "qr": qr}
            else:
                logger.error(f"Error al crear sesión WAHA: {response.text}")
                return {"status": "error", "error": response.text}
    except Exception as e:
        logger.error(f"Excepción al crear sesión WAHA: {str(e)}")
        return {"status": "error", "error": str(e)}


async def sync_waha_chat_history(
    session_name: str, agent_id: str, db_session
) -> dict:
    """
    Sincroniza el historial de chats (últimos 3 meses) desde WAHA hacia la BD local.
    Crea conversaciones y mensajes históricos para que el agente tenga contexto.
    Retorna estadísticas de la sincronización.
    """
    if waha_is_mock_mode():
        return {"status": "mock", "chats": 0, "messages": 0}

    from models.conversation import Conversation, Message
    from datetime import datetime, timezone, timedelta

    three_months_ago = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp())
    headers = _headers()
    stats = {"chats": 0, "messages": 0, "errors": 0}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Obtener todos los chats
            chats_url = f"{settings.waha_api_url}/api/{session_name}/chats"
            chats_resp = await client.get(chats_url, headers=headers)
            if chats_resp.status_code != 200:
                logger.warning(f"[WAHA SYNC] No se pudieron obtener chats: {chats_resp.status_code}")
                return {"status": "error", "error": f"HTTP {chats_resp.status_code}"}

            chats_data = chats_resp.json()
            if not isinstance(chats_data, list):
                chats_data = chats_data.get("chats", []) if isinstance(chats_data, dict) else []

            logger.info(f"[WAHA SYNC] Se encontraron {len(chats_data)} chats para sincronizar.")

            for chat in chats_data:
                chat_id = chat.get("id", "")
                if not chat_id:
                    continue

                contact_phone = chat_id.replace("@c.us", "").replace("@s.whatsapp.net", "")
                contact_name = chat.get("name") or chat.get("pushName") or ""

                # 2. Obtener mensajes del chat (últimos 3 meses)
                msgs_url = (
                    f"{settings.waha_api_url}/api/{session_name}/chats/"
                    f"{chat_id}/messages?limit=100&filter.timestamp.gte={three_months_ago}"
                )
                msgs_resp = await client.get(msgs_url, headers=headers)
                if msgs_resp.status_code != 200:
                    stats["errors"] += 1
                    continue

                msgs_data = msgs_resp.json()
                if not isinstance(msgs_data, list):
                    continue

                if not msgs_data:
                    continue

                # 3. Buscar o crear conversación en BD
                conversation = (
                    db_session.query(Conversation)
                    .filter(
                        Conversation.agent_id == agent_id,
                        Conversation.contact_phone == contact_phone,
                    )
                    .first()
                )
                if not conversation:
                    conversation = Conversation(
                        agent_id=agent_id,
                        contact_phone=contact_phone,
                        contact_name=contact_name,
                        channel="whatsapp",
                        status="active",
                    )
                    db_session.add(conversation)
                    db_session.flush()

                # 4. Insertar mensajes históricos (omitir duplicados por contenido + rol + timestamp)
                existing_ids = set(
                    row[0] for row in db_session.query(Message.whatsapp_message_id)
                    .filter(Message.conversation_id == conversation.id)
                    .all()
                    if row[0]
                )

                inserted = 0
                for msg in msgs_data:
                    msg_id = msg.get("id", "")
                    if msg_id and msg_id in existing_ids:
                        continue
                    msg_body = msg.get("body") or msg.get("text") or ""
                    if not msg_body:
                        continue
                    is_from_me = msg.get("fromMe", False)
                    timestamp = msg.get("timestamp")
                    sent_at = (
                        datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        if timestamp else datetime.now(timezone.utc)
                    )

                    new_msg = Message(
                        conversation_id=conversation.id,
                        role="assistant" if is_from_me else "user",
                        content=msg_body,
                        whatsapp_message_id=msg_id or None,
                        sent_at=sent_at,
                    )
                    db_session.add(new_msg)
                    inserted += 1

                if inserted > 0:
                    db_session.commit()
                    stats["messages"] += inserted
                    stats["chats"] += 1
                    logger.info(f"[WAHA SYNC] Chat {contact_phone}: {inserted} mensajes insertados.")

            logger.info(f"[WAHA SYNC] Completado: {stats['chats']} chats, {stats['messages']} mensajes.")
            return {"status": "completed", **stats}

    except Exception as e:
        logger.error(f"[WAHA SYNC] Error: {str(e)}")
        return {"status": "error", "error": str(e)}


async def get_waha_qr(session_name: str) -> str | None:
    """Obtiene el código QR en base64 de la sesión usando /api/{session}/auth/qr."""
    if waha_is_mock_mode():
        session = mock_sessions.get(session_name)
        return session.get("qr") if session else MOCK_QR_BASE64

    headers = _headers()
    headers["Accept"] = "application/json"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Intentar primero sin ?format=image (devuelve JSON con base64)
            url = f"{settings.waha_api_url}/api/{session_name}/auth/qr"
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                try:
                    data = response.json()
                    b64 = data.get("data") or data.get("base64") or ""
                    if b64:
                        return f"data:{data.get('mimetype', 'image/png')};base64,{b64}"
                except Exception:
                    pass

            # Fallback: con ?format=image (WAHA devuelve raw PNG)
            url2 = f"{settings.waha_api_url}/api/{session_name}/auth/qr?format=image"
            response2 = await client.get(url2, headers=headers)
            if response2.status_code == 200:
                raw_bytes = response2.content
                if raw_bytes:
                    import base64
                    b64_str = base64.b64encode(raw_bytes).decode("ascii")
                    return f"data:image/png;base64,{b64_str}"

            logger.error(f"Error al obtener QR de WAHA (status {response.status_code}): {response.text[:200]}")
            return get_cached_waha_qr(session_name)
    except Exception as e:
        logger.error(f"Excepción al obtener QR de WAHA: {str(e)}")
        return get_cached_waha_qr(session_name)


async def verify_waha_connection(session_name: str) -> dict:
    """Verifica el estado de la sesión WAHA."""
    if waha_is_mock_mode():
        session = mock_sessions.get(session_name, {"status": "SCAN_QR"})
        connected = session.get("status") == "CONNECTED"
        return {
            "connected": connected,
            "phone_number": session.get("phone"),
            "display_name": session.get("display_name"),
            "error": None,
        }

    url = f"{settings.waha_api_url}/api/sessions/{session_name}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=_headers())
            if response.status_code == 200:
                data = response.json()
                state = (data.get("status") or "").upper()
                connected = state in ("CONNECTED", "WORKING") or data.get("connected") is True
                me = data.get("me") or {}
                return {
                    "connected": connected,
                    "phone_number": str(me.get("id", "")).split("@")[0] or None,
                    "display_name": me.get("pushName") or me.get("name"),
                    "error": None,
                }
            return {
                "connected": False,
                "phone_number": None,
                "display_name": None,
                "error": response.text,
            }
    except Exception as e:
        logger.error(f"Excepción al verificar estado WAHA: {str(e)}")
        return {
            "connected": False,
            "phone_number": None,
            "display_name": None,
            "error": str(e),
        }


async def delete_waha_session(session_name: str) -> bool:
    """Elimina la sesión en WAHA."""
    if waha_is_mock_mode():
        mock_sessions.pop(session_name, None)
        return True

    url = f"{settings.waha_api_url}/api/sessions/{session_name}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.delete(url, headers=_headers())
            return res.status_code in [200, 201, 204, 404]
    except Exception as e:
        logger.error(f"Excepción al eliminar sesión WAHA: {str(e)}")
        return False


async def send_waha_text_raw(session_name: str, to_phone: str, text: str) -> bool:
    """Envía un mensaje de texto plano vía WAHA sin procesar Markdown."""
    if waha_is_mock_mode():
        print(f"[WAHA SEND MOCK] {session_name} -> {to_phone}: {text[:80]}")
        logger.info(f"[MOCK WAHA SEND] {session_name} -> {to_phone}: {text[:80]}")
        return True

    url = f"{settings.waha_api_url}/api/sendText"
    payload = {
        "session": session_name,
        "chatId": _normalize_chat_id(to_phone),
        "text": text,
    }
    print(f"[WAHA SEND RAW] Enviando a {url}. session={session_name}, to={to_phone}, text={text[:60]}")
    logger.info("Enviando mensaje WAHA a %s en sesión %s: text_len=%d", to_phone, session_name, len(text))
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=_headers(), json=payload)
            print(f"[WAHA SEND RAW] Respuesta del servidor WAHA: status={response.status_code}, payload={response.text[:200]}")
            if response.status_code in [200, 201]:
                logger.info("Mensaje WAHA enviado a %s (status=%d)", to_phone, response.status_code)
                return True
            logger.error("Error al enviar texto WAHA (status=%d): %s", response.status_code, response.text)
            return False
    except Exception as e:
        print(f"[WAHA SEND RAW] EXCEPCIÓN enviando mensaje: {e}")
        logger.error("Excepción al enviar texto WAHA: %s", str(e))
        return False


async def send_waha_text(session_name: str, to_phone: str, text: str) -> bool:
    """
    Envía un mensaje de texto vía WAHA.
    Detecta de forma inteligente cualquier imagen (formatos Markdown ![alt](url), enlaces [alt](url)
    o URLs directas de Supabase Storage / imágenes), las extrae del cuerpo del mensaje y las envía
    como fotos multimedia nativas en WhatsApp.
    """
    import re
    
    found_images = []
    cleaned_text = text

    # 1. Encontrar etiquetas Markdown de imagen ![caption](url) y enlaces [caption](url_imagen)
    markdown_pattern = r'!?\[(.*?)\]\((https?://[^\s\)]+)\)'
    for match in re.finditer(markdown_pattern, cleaned_text):
        caption, url = match.group(1), match.group(2)
        url_lower = url.lower()
        if any(ext in url_lower for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', 'supabase.co/storage']):
            if (caption, url) not in found_images:
                found_images.append((caption, url))

    # 2. Encontrar URLs sueltas de Supabase o imágenes directas
    raw_url_pattern = r'(https?://[^\s\)]+?(?:supabase\.co/storage/v1/object/public/[^\s\)]+|\.(?:png|jpg|jpeg|webp)))'
    for match in re.finditer(raw_url_pattern, cleaned_text):
        url = match.group(1)
        if not any(url == item[1] for item in found_images):
            found_images.append(("", url))

    if found_images:
        # Remover de forma limpia las URLs y marcas de agua de markdown del texto
        cleaned_text = re.sub(r'!?\[(.*?)\]\((https?://[^\s\)]+)\)', '', cleaned_text)
        cleaned_text = re.sub(raw_url_pattern, '', cleaned_text)
        cleaned_text = re.sub(r'^\s*ppzsnsovdmxwofmuppfv\.supabase\.co\s*', '', cleaned_text, flags=re.MULTILINE)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text).strip()
        
        success = True
        if cleaned_text:
            success = await send_waha_text_raw(session_name, to_phone, cleaned_text)
            
        for caption, image_url in found_images:
            logger.info(f"[WAHA MULTIMEDIA] Enviando foto nativa a {to_phone}: {image_url}")
            img_success = await send_waha_image(session_name, to_phone, image_url, caption)
            success = success and img_success
            
        return success
    else:
        return await send_waha_text_raw(session_name, to_phone, text)


async def send_waha_image(session_name: str, to_phone: str, image_url: str, caption: str = "") -> bool:
    """Envía una imagen nativa vía WAHA."""
    if waha_is_mock_mode():
        logger.info(f"[MOCK WAHA IMAGE] {session_name} -> {to_phone}: {image_url}")
        return True

    url = f"{settings.waha_api_url}/api/sendImage"
    payload = {
        "session": session_name,
        "chatId": _normalize_chat_id(to_phone),
        "file": {
            "mimetype": "image/jpeg",
            "url": image_url,
            "filename": "image.jpeg"
        },
        "caption": caption,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=_headers(), json=payload)
            if response.status_code in [200, 201]:
                return True
            logger.error("Error al enviar imagen WAHA (status=%d): %s", response.status_code, response.text)
            return False
    except Exception as e:
        logger.error("Excepción al enviar imagen WAHA: %s", str(e))
        return False


async def restart_waha_session(session_name: str, webhook_url: str = "") -> str | None:
    """Reinicia la sesión para regenerar un QR limpio."""
    if waha_is_mock_mode():
        return MOCK_QR_BASE64

    # WAHA: logout y luego start nuevamente
    logout_url = f"{settings.waha_api_url}/api/sessions/{session_name}/logout"
    start_url = f"{settings.waha_api_url}/api/sessions/{session_name}/start"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                await client.post(logout_url, headers=_headers())
            except Exception:
                pass
            payload = {"start": True}
            if webhook_url:
                payload["config"] = {
                    "webhooks": [{
                        "url": webhook_url,
                        "events": ["message", "session.status"],
                    }],
                }
            res = await client.post(start_url, headers=_headers(), json=payload)
            if res.status_code in [200, 201]:
                data = res.json()
                qr = data.get("qr") or (data.get("qrcode") or None)
                if qr:
                    store_waha_qr(session_name, qr)
                return qr
            logger.warning("No se pudo reiniciar sesión WAHA: %s", res.text)
            return None
    except Exception as e:
        logger.error(f"Excepción al reiniciar sesión WAHA: {str(e)}")
        return None


async def auto_recover_waha_session(agent, webhook_url: str, db_session=None) -> dict:
    """
    Detecta si la sesión WAHA de un agente está perdida y la recrea automáticamente.
    Retorna el nuevo QR si se creó, o el estado actual si ya está conectada.
    """
    session_name = agent.whatsapp_qr_instance_name if hasattr(agent, "whatsapp_qr_instance_name") else None

    if session_name:
        verification = await verify_waha_connection(session_name)
        if verification.get("connected"):
            logger.info(f"[AUTO-RECOVER] Sesión '{session_name}' ya conectada. No requiere recuperación.")
            return {"recovered": True, "session_name": session_name, "qr": None, "action": "already_connected"}

        error_str = verification.get("error") or ""
        session_exists = not ("Session not found" in error_str or "404" in error_str)

        if session_exists and verification.get("connected") is False:
            logger.info(f"[AUTO-RECOVER] Sesión '{session_name}' existe pero desconectada. Reiniciando...")
            qr = await restart_waha_session(session_name, webhook_url)
            if qr:
                return {"recovered": True, "session_name": session_name, "qr": qr, "action": "restarted"}
            logger.warning(f"[AUTO-RECOVER] No se pudo reiniciar sesión '{session_name}', se creará una nueva.")

    import time
    new_name = f"genia_{str(agent.id)[:8]}_{int(time.time())}"
    logger.info(f"[AUTO-RECOVER] Creando nueva sesión WAHA '{new_name}' para agente '{agent.name}'.")

    result = await create_waha_session(new_name, webhook_url)
    if result.get("status") == "error":
        logger.error(f"[AUTO-RECOVER] Error creando sesión: {result.get('error')}")
        return {"recovered": False, "error": result.get("error")}

    qr = result.get("qr")
    if qr:
        store_waha_qr(new_name, qr)

    # Actualizar BD si hay sesión de DB disponible
    if db_session is not None:
        try:
            agent.whatsapp_qr_instance_name = new_name
            agent.whatsapp_qr_code = qr or agent.whatsapp_qr_code
            agent.whatsapp_qr_connected = False
            agent.whatsapp_provider = "waha"
            db_session.commit()
            logger.info(f"[AUTO-RECOVER] BD actualizada con nueva sesión '{new_name}'.")
        except Exception as e:
            db_session.rollback()
            logger.error(f"[AUTO-RECOVER] Error actualizando BD: {e}")

    return {
        "recovered": True,
        "session_name": new_name,
        "qr": qr,
        "action": "created",
    }


async def monitor_and_recover_all_agents(db_session=None) -> dict:
    """
    Monitorea todos los agentes con proveedor WAHA y recupera sesiones perdidas.
    Debe ejecutarse periódicamente (cada 5-10 minutos) para mantener estabilidad.
    
    MEJORA: Cuando detecta sesiones perdidas, intenta RECONECTAR automáticamente
    usando las cookies persistidas en el volumen Docker antes de rendirse.
    Si no puede reconectar, notifica al propietario del agente.
    """
    if waha_is_mock_mode():
        return {"mode": "mock", "message": "Modo mock, sin monitoreo de sesiones"}

    try:
        from sqlalchemy.orm import Session
        from models.agent import Agent

        if db_session is None:
            return {"error": "Se requiere db_session para monitorear agentes"}

        agents = db_session.query(Agent).filter(
            Agent.whatsapp_provider == "waha",
            Agent.status == "active",
        ).all()

        waha_sessions = await list_waha_sessions()
        waha_session_names = {s.get("name", "") for s in waha_sessions}
        waha_working_names = {
            s.get("name", "")
            for s in waha_sessions
            if s.get("status", "").upper() in ("WORKING", "CONNECTED")
        }
        # Sesiones en estado FAILED o DISCONNECTED que podrían reiniciarse
        waha_failed_names = {
            s.get("name", ""): s.get("status", "").upper()
            for s in waha_sessions
            if s.get("status", "").upper() in ("FAILED", "DISCONNECTED", "STOPPED")
        }

        results = []
        agents_needing_qr = []  # Agentes que definitivamente necesitan QR nuevo

        for agent in agents:
            db_name = agent.whatsapp_qr_instance_name
            agent_prefix = f"genia_{str(agent.id)[:8]}"
            was_connected = agent.whatsapp_qr_connected  # ¿Estaba conectado antes?

            # Buscar sesión activa por prefijo
            found_working = [n for n in waha_working_names if n.startswith(agent_prefix)]
            found_any = [n for n in waha_session_names if n.startswith(agent_prefix)]
            found_failed = {n: st for n, st in waha_failed_names.items() if n.startswith(agent_prefix)}

            if found_working:
                working_name = found_working[0]
                if db_name != working_name:
                    logger.info(f"[MONITOR] Actualizando BD: {db_name} -> {working_name}")
                    agent.whatsapp_qr_instance_name = working_name
                    agent.whatsapp_qr_connected = True
                    agent.whatsapp_qr_code = None
                    agent.whatsapp_provider = "waha"
                    db_session.commit()
                    results.append({"agent": str(agent.id), "name": agent.name, "action": "sync_working", "session": working_name})
                else:
                    results.append({"agent": str(agent.id), "name": agent.name, "action": "already_working", "session": working_name})

            elif found_failed:
                # ===== NUEVO: Intentar REINICIAR sesiones FAILED/DISCONNECTED =====
                failed_name = list(found_failed.keys())[0]
                failed_status = found_failed[failed_name]
                logger.warning(f"[MONITOR] Sesión '{failed_name}' en estado {failed_status} para agente '{agent.name}'. Intentando restart con cookies...")

                restart_ok = await restart_waha_session_by_name(failed_name)
                if restart_ok:
                    agent.whatsapp_qr_instance_name = failed_name
                    agent.whatsapp_qr_connected = True
                    agent.whatsapp_qr_code = None
                    db_session.commit()
                    logger.info(f"[MONITOR] ✅ Sesión '{failed_name}' RECONECTADA con cookies para agente '{agent.name}'.")
                    results.append({"agent": str(agent.id), "name": agent.name, "action": "auto_restarted", "session": failed_name})
                else:
                    # No se pudo reconectar con cookies — se necesita QR nuevo
                    logger.warning(f"[MONITOR] ❌ No se pudo reconectar '{failed_name}'. Se requiere QR nuevo para agente '{agent.name}'.")
                    agent.whatsapp_qr_instance_name = None
                    agent.whatsapp_qr_connected = False
                    db_session.commit()
                    agents_needing_qr.append(agent)
                    results.append({"agent": str(agent.id), "name": agent.name, "action": "restart_failed_needs_qr", "session": failed_name})
                    # Notificar al propietario si estaba conectado antes
                    if was_connected:
                        await send_disconnect_notification(agent, db_session, reason=f"Sesión '{failed_name}' falló y no se pudo reconectar")

            elif found_any:
                any_name = found_any[0]
                logger.info(f"[MONITOR] Sesión '{any_name}' existe pero no está WORKING. Verificando...")
                verification = await verify_waha_connection(any_name)
                if verification.get("connected"):
                    agent.whatsapp_qr_instance_name = any_name
                    agent.whatsapp_qr_connected = True
                    agent.whatsapp_qr_code = None
                    db_session.commit()
                    results.append({"agent": str(agent.id), "name": agent.name, "action": "recovered", "session": any_name})
                else:
                    # Intentar restart antes de limpiar
                    logger.info(f"[MONITOR] Intentando restart de sesión '{any_name}' antes de limpiar...")
                    restart_ok = await restart_waha_session_by_name(any_name)
                    if restart_ok:
                        agent.whatsapp_qr_instance_name = any_name
                        agent.whatsapp_qr_connected = True
                        agent.whatsapp_qr_code = None
                        db_session.commit()
                        results.append({"agent": str(agent.id), "name": agent.name, "action": "auto_restarted", "session": any_name})
                    else:
                        if agent.whatsapp_qr_instance_name == any_name:
                            agent.whatsapp_qr_instance_name = None
                            agent.whatsapp_qr_connected = False
                            db_session.commit()
                        agents_needing_qr.append(agent)
                        results.append({"agent": str(agent.id), "name": agent.name, "action": "stale_cleaned", "session": any_name})
                        if was_connected:
                            await send_disconnect_notification(agent, db_session, reason=f"Sesión '{any_name}' perdió conexión")
            else:
                # No hay sesión en WAHA para este agente
                if db_name and db_name in waha_session_names:
                    verification = await verify_waha_connection(db_name)
                    if verification.get("connected"):
                        agent.whatsapp_qr_connected = True
                        db_session.commit()
                        results.append({"agent": str(agent.id), "name": agent.name, "action": "verified_connected", "session": db_name})
                        continue
                if db_name:
                    logger.info(f"[MONITOR] Sesión '{db_name}' perdida para agente '{agent.name}'. Intentando crear y reconectar...")
                    # Intentar crear sesión con el mismo nombre (WAHA puede tener cookies)
                    restart_ok = await restart_waha_session_by_name(db_name)
                    if restart_ok:
                        agent.whatsapp_qr_connected = True
                        db_session.commit()
                        logger.info(f"[MONITOR] ✅ Sesión '{db_name}' recreada con cookies para '{agent.name}'.")
                        results.append({"agent": str(agent.id), "name": agent.name, "action": "auto_recreated", "session": db_name})
                    else:
                        agent.whatsapp_qr_instance_name = None
                        agent.whatsapp_qr_connected = False
                        db_session.commit()
                        agents_needing_qr.append(agent)
                        results.append({"agent": str(agent.id), "name": agent.name, "action": "lost_needs_qr", "session": db_name})
                        if was_connected:
                            await send_disconnect_notification(agent, db_session, reason=f"Sesión '{db_name}' desapareció del servidor WAHA")
                else:
                    results.append({"agent": str(agent.id), "name": agent.name, "action": "no_session", "session": None})

        return {
            "mode": "production",
            "total_agents": len(agents),
            "results": results,
            "agents_needing_qr": [str(a.id) for a in agents_needing_qr],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error en monitor_and_recover_all_agents: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def send_disconnect_notification(agent, db_session, reason: str = ""):
    """
    Envía una notificación al propietario del agente cuando la sesión de WhatsApp
    se desconecta y no se puede reconectar automáticamente.
    """
    try:
        notification_phone = getattr(agent, "notification_phone", None)
        if not notification_phone:
            logger.info(f"[NOTIFY] Agente '{agent.name}' no tiene notification_phone. No se envía alerta.")
            return

        from datetime import datetime, timezone
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        notification_text = (
            f"⚠️ *Alerta: Agente '{agent.name}' Desconectado de WhatsApp*\n\n"
            f"El agente dejó de responder mensajes de WhatsApp.\n"
            f"Motivo: {reason}\n\n"
            f"*Acción requerida:* Ingresa al panel de GENIA y reconecta "
            f"el agente escaneando un nuevo código QR.\n\n"
            f"🔗 https://genia.com.co/app\n"
            f"📅 {now_str}"
        )

        # Intentar enviar por la sesión del mismo agente (probablemente no funcione
        # porque está desconectada), así que intentamos por cualquier otro agente activo
        from models.agent import Agent

        other_agents = db_session.query(Agent).filter(
            Agent.whatsapp_provider == "waha",
            Agent.status == "active",
            Agent.whatsapp_qr_connected == True,
            Agent.whatsapp_qr_instance_name.isnot(None),
            Agent.id != agent.id,
        ).all()

        sent = False
        for other in other_agents:
            try:
                ok = await send_waha_text(
                    session_name=other.whatsapp_qr_instance_name,
                    to_phone=notification_phone,
                    text=notification_text,
                )
                if ok:
                    logger.info(f"[NOTIFY] Notificación enviada a {notification_phone} vía agente '{other.name}'.")
                    sent = True
                    break
            except Exception:
                continue

        if not sent:
            logger.warning(
                f"[NOTIFY] No se pudo enviar notificación de desconexión para '{agent.name}' a {notification_phone}. "
                f"No hay otros agentes WAHA activos para enviar el mensaje."
            )
    except Exception as e:
        logger.error(f"[NOTIFY] Error enviando notificación de desconexión: {e}")


async def check_waha_health() -> dict:
    """Verifica la conectividad con el servidor WAHA."""
    if waha_is_mock_mode():
        return {"healthy": True, "mode": "mock", "error": None}

    if not settings.waha_api_url:
        return {"healthy": False, "error": "WAHA_API_URL no configurada"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{settings.waha_api_url}/api/version"
            response = await client.get(url, headers=_headers())
            if response.status_code in [200, 201]:
                return {"healthy": True, "mode": "production", "error": None}
            return {
                "healthy": False,
                "error": f"WAHA respondió status {response.status_code}: {response.text[:200]}",
            }
    except Exception as e:
        return {"healthy": False, "error": f"No se pudo conectar a WAHA: {str(e)}"}


async def set_waha_presence(session_name: str, to_phone: str, presence: str = "typing") -> bool:
    """
    Establece el estado de presencia (typing, paused, online, offline) para un chat o globalmente.
    """
    if waha_is_mock_mode():
        logger.info(f"[MOCK WAHA PRESENCE] {session_name} -> {to_phone}: {presence}")
        return True

    url = f"{settings.waha_api_url}/api/{session_name}/presence"
    payload = {
        "presence": presence
    }
    if to_phone:
        payload["chatId"] = _normalize_chat_id(to_phone)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=_headers(), json=payload)
            if response.status_code in [200, 201]:
                return True
            logger.warning("Error al establecer presencia en WAHA: %s", response.text)
            return False
    except Exception as e:
        logger.error("Excepción al establecer presencia en WAHA: %s", str(e))
        return False


def simulate_waha_scan(session_name: str, phone: str = "573103125460") -> bool:
    """Simula el escaneo del QR en modo local/desarrollo."""
    if session_name in mock_sessions:
        mock_sessions[session_name]["status"] = "CONNECTED"
        mock_sessions[session_name]["phone"] = phone
        mock_sessions[session_name]["display_name"] = "Cliente WAHA Mock"
        logger.info(f"[MOCK WAHA] Sesión '{session_name}' simulada como CONECTADA.")
        return True
    return False
