import os
import logging
import base64
import httpx
from fastapi import FastAPI, Request, Response, status

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audio_proxy")

app = FastAPI(title="Genia Audio Proxy")

# Variables de entorno
GENIA_BACKEND_URL = os.getenv("GENIA_BACKEND_URL", "https://plataforma-genia.vercel.app")
WAHA_LOCAL_URL = os.getenv("WAHA_LOCAL_URL", "http://waha:3000")
WAHA_API_KEY = os.getenv("WAHA_API_KEY", "")

@app.post("/webhook/waha/{agent_id}")
async def receive_webhook(agent_id: str, request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Error parseando JSON: {str(e)}")
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid JSON")

    event = data.get("event", "")
    payload = data.get("payload", {}) or {}
    msg_type = payload.get("type", "")

    logger.info(f"Webhook recibido para agent_id={agent_id}, event={event}, msg_type={msg_type}")

    # Verificar si es nota de voz o audio
    is_voice = event == "message" and msg_type in ("ptt", "audio")
    
    if is_voice:
        media_url = payload.get("media", "") or payload.get("mediaUrl", "")
        logger.info(f"Detectada nota de voz. URL original: {media_url}")
        
        if media_url and "localhost" in media_url:
            # Reemplazar localhost por el nombre del servicio docker 'waha' en la red interna
            internal_media_url = media_url.replace("localhost:3000", "waha:3000").replace("127.0.0.1:3000", "waha:3000")
            # Por si acaso el puerto es 3100
            internal_media_url = internal_media_url.replace("localhost:3100", "waha:3000").replace("127.0.0.1:3100", "waha:3000")
            
            logger.info(f"Descargando audio desde URL interna: {internal_media_url}")
            
            headers = {}
            if WAHA_API_KEY:
                headers["X-Api-Key"] = WAHA_API_KEY
                
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.get(internal_media_url, headers=headers)
                    if res.status_code == 200:
                        audio_bytes = res.content
                        base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                        # Inyectar el base64 en payload para que backend lo lea
                        payload["base64"] = base64_audio
                        logger.info(f"Audio descargado con éxito ({len(audio_bytes)} bytes) y codificado en Base64")
                    else:
                        logger.error(f"Fallo al descargar audio local. Status: {res.status_code}, Body: {res.text[:100]}")
            except Exception as dl_err:
                logger.error(f"Error descargando audio del servidor local: {str(dl_err)}")

    # Reenviar al Backend de Genia en Vercel
    vercel_url = f"{GENIA_BACKEND_URL.rstrip('/')}/api/whatsapp/webhook/waha/{agent_id}"
    logger.info(f"Reenviando webhook a Vercel: {vercel_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Content-Type": "application/json"}
            vercel_res = await client.post(vercel_url, json=data, headers=headers)
            logger.info(f"Respuesta de Vercel: status={vercel_res.status_code}")
            return Response(status_code=vercel_res.status_code, content=vercel_res.content)
    except Exception as fw_err:
        logger.error(f"Error reenviando webhook a Vercel: {str(fw_err)}")
        return Response(status_code=status.HTTP_202_ACCEPTED, content="Failed to forward but accepted")
