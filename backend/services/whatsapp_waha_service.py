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
"""

import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

# Diccionario en memoria para simular sesiones WAHA en desarrollo local
mock_sessions = {}

# Caché del último QR entregado por el evento webhook 'qr' (WAHA 2024+ solo
# entrega el QR vía webhook, no por REST). Clave: session_name -> qr base64.
waha_qr_cache: dict[str, str] = {}


def store_waha_qr(session_name: str, qr: str) -> None:
    """Guarda el QR más reciente recibido por webhook para servirlo al frontend."""
    if session_name and qr:
        waha_qr_cache[session_name] = qr


def get_cached_waha_qr(session_name: str) -> str | None:
    """Recupera el último QR conocido desde la caché de webhook."""
    return waha_qr_cache.get(session_name)

MOCK_QR_BASE64 = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJQAAACUAQMAAABvMD4ZAAAAA1BMVEUAAACnej3aAAAA"
    "AXRSTlMAQObYZgAAAAlwSFlzAAAOxAAADsQBlbZJywAAABpJREFUeNpiYGBgYGBgYGBgYGBgYGBgYGBgYADADAADwAB"
    "g4m4AAAAASUVORK5CYII="
)


def waha_is_mock_mode() -> bool:
    """Retorna True si no está configurada la URL de WAHA."""
    return not settings.waha_api_url


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


async def create_waha_session(session_name: str, webhook_url: str) -> dict:
    """
    Crea (o reutiliza) una sesión en WAHA y retorna el QR inicial.
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

    url = f"{settings.waha_api_url}/api/sessions/start"
    payload = {
        "name": session_name,
        "webhooks": [{"url": webhook_url}],
        "waitForScan": True,
    }
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


async def get_waha_qr(session_name: str) -> str | None:
    """Obtiene el código QR en base64 de la sesión usando /api/{session}/auth/qr."""
    if waha_is_mock_mode():
        session = mock_sessions.get(session_name)
        return session.get("qr") if session else MOCK_QR_BASE64

    url = f"{settings.waha_api_url}/api/{session_name}/auth/qr?format=image"
    headers = _headers()
    headers["Accept"] = "application/json"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                try:
                    data = response.json()
                    # WAHA devuelve {"mimetype": "image/png", "data": "base64..."}
                    b64 = data.get("data") or data.get("base64") or ""
                    if b64:
                        return f"data:{data.get('mimetype', 'image/png')};base64,{b64}"
                except Exception:
                    text = response.text.strip()
                    if text.startswith("data:image"):
                        return text
                    return text or None
            else:
                logger.error(f"Error al obtener QR de WAHA: {response.text[:200]}")
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


async def send_waha_text(session_name: str, to_phone: str, text: str) -> bool:
    """Envía un mensaje de texto plano vía WAHA."""
    if waha_is_mock_mode():
        logger.info(f"[MOCK WAHA SEND] {session_name} -> {to_phone}: {text[:80]}")
        return True

    url = f"{settings.waha_api_url}/api/sendText"
    payload = {
        "session": session_name,
        "chatId": _normalize_chat_id(to_phone),
        "text": text,
    }
    logger.info("Enviando mensaje WAHA a %s en sesión %s: text_len=%d", to_phone, session_name, len(text))
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=_headers(), json=payload)
            if response.status_code in [200, 201]:
                logger.info("Mensaje WAHA enviado a %s (status=%d)", to_phone, response.status_code)
                return True
            logger.error("Error al enviar texto WAHA (status=%d): %s", response.status_code, response.text)
            return False
    except Exception as e:
        logger.error("Excepción al enviar texto WAHA: %s", str(e))
        return False


async def send_waha_image(session_name: str, to_phone: str, image_url: str, caption: str = "") -> bool:
    """Envía una imagen nativa vía WAHA."""
    if waha_is_mock_mode():
        logger.info(f"[MOCK WAHA IMAGE] {session_name} -> {to_phone}: {image_url}")
        return True

    url = f"{settings.waha_api_url}/api/sendImage"
    payload = {
        "session": session_name,
        "chatId": _normalize_chat_id(to_phone),
        "media": {"url": image_url},
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


async def restart_waha_session(session_name: str) -> str | None:
    """Reinicia la sesión para regenerar un QR limpio."""
    if waha_is_mock_mode():
        return MOCK_QR_BASE64

    # WAHA: logout y luego start nuevamente
    logout_url = f"{settings.waha_api_url}/api/{session_name}/logout"
    start_url = f"{settings.waha_api_url}/api/sessions/start"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                await client.post(logout_url, headers=_headers())
            except Exception:
                pass
            payload = {"name": session_name, "webhooks": [], "waitForScan": True}
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


def simulate_waha_scan(session_name: str, phone: str = "573103125460") -> bool:
    """Simula el escaneo del QR en modo local/desarrollo."""
    if session_name in mock_sessions:
        mock_sessions[session_name]["status"] = "CONNECTED"
        mock_sessions[session_name]["phone"] = phone
        mock_sessions[session_name]["display_name"] = "Cliente WAHA Mock"
        logger.info(f"[MOCK WAHA] Sesión '{session_name}' simulada como CONECTADA.")
        return True
    return False
