"""
Servicio para interactuar con APIs de emulación de WhatsApp (vía Código QR) como Evolution API.

Incluye soporte completo de simulación (Mock) si no se configuran variables de entorno,
lo que permite probar el flujo de escaneo y mensajería en desarrollo local.
"""

import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

# Diccionario en memoria para simular sesiones QR en desarrollo local
# Formato: { instance_name: { "status": "disconnected"|"connected", "qr": "base64...", "phone": "..." } }
mock_sessions = {}

# QR de prueba (1x1 píxel negro o imagen de caja QR en base64)
MOCK_QR_BASE64 = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJQAAACUAQMAAABvMD4ZAAAAA1BMVEUAAACnej3aAAAA"
    "AXRSTlMAQObYZgAAAAlwSFlzAAAOxAAADsQBlbZJywAAABpJREFUeNpiYGBgYGBgYGBgYGBgYGBgYGBgYADADAADwAB"
    "g4m4AAAAASUVORK5CYII="
)


def is_mock_mode() -> bool:
    """Retorna True si no están configuradas las credenciales de Evolution API."""
    return not settings.evolution_api_url or not settings.evolution_api_token


async def create_qr_instance(instance_name: str) -> dict:
    """
    Crea una nueva instancia en Evolution API o simula su creación.
    """
    if is_mock_mode():
        logger.info(f"[MOCK QR] Creando instancia simulada: '{instance_name}'")
        mock_sessions[instance_name] = {
            "status": "disconnected",
            "qr": MOCK_QR_BASE64,
            "phone": None,
            "display_name": None
        }
        return {"status": "created", "instance": instance_name}

    url = f"{settings.evolution_api_url}/instance/create"
    headers = {
        "apikey": settings.evolution_api_token,
        "Content-Type": "application/json"
    }
    payload = {
        "instanceName": instance_name,
        "token": f"token_{instance_name}",
        "integration": "WHATSAPP-BAILEYS",
        "reject_call": False,
        "msgCall": "",
        "groupsIgnore": True,
        "alwaysOnline": True,
        "readMessages": True,
        "readStatus": False
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                data = response.json()
                hash_data = data.get("hash")
                token_val = None
                if isinstance(hash_data, dict):
                    token_val = hash_data.get("token")
                elif isinstance(hash_data, str):
                    token_val = hash_data
                logger.info(f"Instancia QR '{instance_name}' creada en Evolution API.")
                return {"status": "created", "instance": instance_name, "token": token_val}
            elif response.status_code == 403:
                # La instancia ya existe — esto es válido, simplemente continuamos
                logger.warning(f"Instancia '{instance_name}' ya existe en Evolution API. Reutilizando.")
                return {"status": "created", "instance": instance_name, "token": None}
            else:
                logger.error(f"Error al crear instancia en Evolution API: {response.text}")
                return {"status": "error", "error": response.text}
    except Exception as e:
        logger.error(f"Excepción al crear instancia en Evolution API: {str(e)}")
        return {"status": "error", "error": str(e)}


async def get_qr_code(instance_name: str) -> str | None:
    """
    Obtiene el código QR en base64 para renderizar en el frontend.
    """
    if is_mock_mode():
        logger.info(f"[MOCK QR] Obteniendo QR simulado para: '{instance_name}'")
        return MOCK_QR_BASE64

    url = f"{settings.evolution_api_url}/instance/connect/{instance_name}"
    headers = {
        "apikey": settings.evolution_api_token
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                # Evolution API retorna el QR en formato base64 en data.get("base64") o data.get("code")
                return data.get("base64") or data.get("code")
            else:
                logger.error(f"Error al obtener QR de Evolution API: {response.text}")
                return None
    except Exception as e:
        logger.error(f"Excepción al obtener QR de Evolution API: {str(e)}")
        return None


async def verify_qr_connection(instance_name: str) -> dict:
    """
    Verifica el estado de conexión de la instancia.
    """
    if is_mock_mode():
        session = mock_sessions.get(instance_name, {"status": "disconnected"})
        if session.get("status") == "connected":
            return {
                "connected": True,
                "phone_number": session.get("phone", "573103125460"),
                "display_name": session.get("display_name", "Línea QR Simulada"),
                "error": None
            }
        return {
            "connected": False,
            "phone_number": None,
            "display_name": None,
            "qr_code": session.get("qr"),
            "error": None
        }

    url = f"{settings.evolution_api_url}/instance/connectionState/{instance_name}"
    headers = {
        "apikey": settings.evolution_api_token
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                state = data.get("instance", {}).get("state")
                connected = (state == "open" or data.get("state") == "open")
                
                # Obtener detalles del número conectado si está abierto
                phone = None
                name = None
                if connected:
                    info_url = f"{settings.evolution_api_url}/instance/info/{instance_name}"
                    info_res = await client.get(info_url, headers=headers)
                    if info_res.status_code == 200:
                        info_data = info_res.json()
                        phone = info_data.get("instance", {}).get("ownerJid", "").split("@")[0]
                        name = info_data.get("instance", {}).get("profileName")

                return {
                    "connected": connected,
                    "phone_number": phone,
                    "display_name": name,
                    "error": None
                }
            else:
                return {
                    "connected": False,
                    "phone_number": None,
                    "display_name": None,
                    "error": response.text
                }
    except Exception as e:
        logger.error(f"Excepción al verificar estado de Evolution API: {str(e)}")
        return {
            "connected": False,
            "phone_number": None,
            "display_name": None,
            "error": str(e)
        }


async def delete_qr_instance(instance_name: str) -> bool:
    """
    Cierra sesión y elimina la instancia en la API.
    """
    if is_mock_mode():
        logger.info(f"[MOCK QR] Eliminando instancia simulada: '{instance_name}'")
        if instance_name in mock_sessions:
            del mock_sessions[instance_name]
        return True

    logout_url = f"{settings.evolution_api_url}/instance/logout/{instance_name}"
    delete_url = f"{settings.evolution_api_url}/instance/delete/{instance_name}"
    headers = {
        "apikey": settings.evolution_api_token
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Intentar logout
            await client.delete(logout_url, headers=headers)
            # 2. Intentar delete
            res = await client.delete(delete_url, headers=headers)
            return res.status_code == 200
    except Exception as e:
        logger.error(f"Excepción al eliminar instancia en Evolution API: {str(e)}")
        return False


async def send_qr_image(instance_name: str, to_phone: str, image_url: str, caption: str = "", token: str = None) -> bool:
    """
    Envía una imagen a través del servicio QR (Evolution API).
    """
    if is_mock_mode():
        logger.info(f"[MOCK QR SEND IMAGE] De: '{instance_name}' Para: '{to_phone}': URL={image_url}, Caption={caption}")
        return True

    auth_token = token or settings.evolution_api_token
    url = f"{settings.evolution_api_url}/message/sendMedia/{instance_name}"
    headers = {
        "apikey": auth_token,
        "Content-Type": "application/json"
    }

    import os
    from urllib.parse import urlparse
    parsed_url = urlparse(image_url)
    filename = os.path.basename(parsed_url.path) or "image.jpg"
    if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        filename = "image.jpg"

    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    mimetype = f"image/{ext}" if ext in ["png", "gif", "webp"] else "image/jpeg"

    payload = {
        "number": to_phone,
        "mediatype": "image",
        "mimetype": mimetype,
        "media": image_url,
        "fileName": filename,
        "caption": caption
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                return True
            logger.error(f"Error al enviar imagen QR de Evolution API: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al enviar imagen QR de Evolution API: {str(e)}")
        return False


async def send_qr_text_raw(instance_name: str, to_phone: str, text: str, token: str = None) -> bool:
    """
    Envía un mensaje de texto puro a través de la Evolution API.
    """
    auth_token = token or settings.evolution_api_token
    url = f"{settings.evolution_api_url}/message/sendText/{instance_name}"
    headers = {
        "apikey": auth_token,
        "Content-Type": "application/json"
    }
    payload = {
        "number": to_phone,
        "text": text,
        "options": {
            "delay": 1000,
            "presence": "composing",
            "linkPreview": False
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                return True
            logger.error(f"Error al enviar mensaje QR de Evolution API: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al enviar mensaje QR de Evolution API: {str(e)}")
        return False


async def send_qr_text(instance_name: str, to_phone: str, text: str, token: str = None) -> bool:
    """
    Envía un mensaje de texto a través del servicio QR.
    Si el texto contiene imágenes en formato Markdown ![alt](url),
    las extrae y las envía como mensajes multimedia nativos de WhatsApp.
    """
    import re
    # Encontrar imágenes en formato ![descripción](url)
    image_matches = re.findall(r'!\[(.*?)\]\((.*?)\)', text)
    
    if image_matches:
        # Extraer texto limpio sin el formato de imagen de markdown
        cleaned_text = re.sub(r'!\[(.*?)\]\((.*?)\)', '', text).strip()
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text).strip()
        
        success = True
        if cleaned_text:
            # Enviar el texto limpio primero
            success = await send_qr_text_raw(instance_name, to_phone, cleaned_text, token)
            
        for caption, image_url in image_matches:
            # Enviar cada imagen de manera nativa
            img_success = await send_qr_image(instance_name, to_phone, image_url, caption, token)
            success = success and img_success
            
        return success
    else:
        return await send_qr_text_raw(instance_name, to_phone, text, token)


async def configure_qr_webhook(instance_name: str, webhook_url: str) -> bool:
    """
    Configura el webhook de eventos entrantes para la instancia en Evolution API.
    """
    if is_mock_mode():
        logger.info(f"[MOCK QR] Configurando webhook simulado en '{instance_name}' apuntando a: {webhook_url}")
        return True

    url = f"{settings.evolution_api_url}/webhook/set/{instance_name}"
    headers = {
        "apikey": settings.evolution_api_token,
        "Content-Type": "application/json"
    }
    payload = {
        "webhook": {
            "enabled": True,
            "url": webhook_url,
            "byEvents": False, # Enviar todos los eventos
            "events": [
                "MESSAGES_UPSERT",
                "CONNECTION_UPDATE"
            ]
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                logger.info(f"Webhook configurado para instancia '{instance_name}'.")
                return True
            logger.error(f"Error al configurar webhook de Evolution API: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al configurar webhook de Evolution API: {str(e)}")
        return False


def simulate_qr_scan(instance_name: str, phone: str = "573103125460") -> bool:
    """
    Simula el escaneo del código QR en modo local/desarrollo.
    """
    if instance_name in mock_sessions:
        mock_sessions[instance_name]["status"] = "connected"
        mock_sessions[instance_name]["phone"] = phone
        mock_sessions[instance_name]["display_name"] = "Cliente QR Mock"
        logger.info(f"[MOCK QR] Instancia '{instance_name}' simulada como CONECTADA con número {phone}.")
        return True
    return False
