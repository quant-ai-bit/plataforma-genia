"""
Servicio para interactuar con la API Cloud de WhatsApp (Meta Graph API).

Permite enviar mensajes de texto, descargar medios, validar firmas HMAC
y verificar la conexión de credenciales de Meta.

Todas las funciones reciben las credenciales como parámetros explícitos
para soportar integración multi-línea por agente.
"""

import hmac
import hashlib
import logging
import httpx

logger = logging.getLogger(__name__)


def verify_whatsapp_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verifica la firma HMAC-SHA256 enviada por Meta en la cabecera X-Hub-Signature-256.

    Args:
        payload: Bytes del cuerpo del request.
        signature: Valor de la cabecera X-Hub-Signature-256 (ej: 'sha256=abcdef...').
        secret: Clave secreta de la aplicación de Meta (app_secret del agente).

    Retorna:
        bool: True si la firma es válida, False en caso contrario.
    """
    if not signature or not secret:
        logger.warning("Falta firma o secreto para validar el webhook de WhatsApp.")
        return False

    if signature.startswith("sha256="):
        signature = signature[7:]

    try:
        # Calcular firma esperada
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Comparación segura en tiempo constante para evitar ataques de temporización
        return hmac.compare_digest(expected_sig, signature)
    except Exception as e:
        logger.error(f"Error al verificar la firma del webhook de WhatsApp: {str(e)}")
        return False


async def send_whatsapp_text(
    to_phone: str,
    text: str,
    phone_number_id: str,
    access_token: str,
) -> dict:
    """
    Envía un mensaje de texto a través de WhatsApp Cloud API.

    Args:
        to_phone: Número de teléfono del destinatario (formato internacional sin +).
        text: Texto del mensaje a enviar.
        phone_number_id: Phone Number ID de Meta del agente.
        access_token: Access Token de Meta del agente.
    """
    if not phone_number_id or not access_token:
        logger.error("Configuración de Meta incompleta (phone_number_id o access_token faltante).")
        raise ValueError("Configuración de Meta incompleta para este agente.")

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.error(f"Error al enviar mensaje de WhatsApp: {response.text}")
        response.raise_for_status()
        return response.json()


async def download_whatsapp_media(
    media_id: str,
    access_token: str,
) -> bytes:
    """
    Descarga un archivo multimedia (audio, imagen, etc.) desde los servidores de Meta.

    Args:
        media_id: ID del medio a descargar.
        access_token: Access Token de Meta del agente.
    """
    if not access_token:
        logger.error("Meta Access Token no configurado para este agente.")
        raise ValueError("Meta Access Token no configurado.")

    url = f"https://graph.facebook.com/v21.0/{media_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with httpx.AsyncClient() as client:
        # Paso 1: Obtener la URL de descarga temporal
        res = await client.get(url, headers=headers)
        res.raise_for_status()
        download_url = res.json().get("url")

        if not download_url:
            raise ValueError(f"No se pudo obtener la URL de descarga para el media ID {media_id}")

        # Paso 2: Descargar los bytes reales
        download_res = await client.get(download_url, headers=headers)
        download_res.raise_for_status()
        return download_res.content


async def verify_whatsapp_connection(
    phone_number_id: str,
    access_token: str,
) -> dict:
    """
    Verifica que las credenciales de Meta sean válidas consultando el endpoint
    de información del número de teléfono.

    Retorna:
        dict con claves:
            - connected (bool): Si la conexión fue exitosa.
            - phone_number (str|None): Número de teléfono verificado.
            - display_name (str|None): Nombre asociado al número.
            - error (str|None): Mensaje de error si falló.
    """
    if not phone_number_id or not access_token:
        return {
            "connected": False,
            "phone_number": None,
            "display_name": None,
            "error": "phone_number_id y access_token son requeridos.",
        }

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "fields": "verified_name,display_phone_number,quality_rating"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                return {
                    "connected": True,
                    "phone_number": data.get("display_phone_number"),
                    "display_name": data.get("verified_name"),
                    "quality_rating": data.get("quality_rating"),
                    "error": None,
                }
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
                logger.warning(
                    f"Verificación de WhatsApp falló para {phone_number_id}: {error_msg}"
                )
                return {
                    "connected": False,
                    "phone_number": None,
                    "display_name": None,
                    "error": error_msg,
                }
    except Exception as e:
        logger.error(f"Error de conexión al verificar WhatsApp: {str(e)}")
        return {
            "connected": False,
            "phone_number": None,
            "display_name": None,
            "error": f"Error de conexión: {str(e)}",
        }


async def send_whatsapp_notification(
    to_phone: str,
    text: str,
    phone_number_id: str = "",
    access_token: str = "",
) -> bool:
    """
    Envía una notificación de WhatsApp al encargado.
    Si la API de Meta no está configurada, simula el envío (útil para pruebas locales).
    """
    if not to_phone:
        logger.warning("No se especificó un número de teléfono de notificación.")
        return False

    try:
        await send_whatsapp_text(to_phone, text, phone_number_id, access_token)
        logger.info(f"Notificación de WhatsApp enviada a {to_phone}: {text}")
        return True
    except Exception as e:
        logger.warning(
            f"[MOCK WHATSAPP] No se pudo enviar notificación a {to_phone} por WhatsApp. "
            f"Detalles: {str(e)}"
        )
        # Para depuración local, imprimimos en consola de forma segura contra errores de encoding
        import sys
        enc = sys.stdout.encoding or "utf-8"
        safe_text = text.encode(enc, errors="replace").decode(enc)
        print(
            f"\n========================================"
            f"\n[WHATSAPP NOTIFICATION TO {to_phone}]"
            f"\n{safe_text}"
            f"\n========================================\n"
        )
        return False
