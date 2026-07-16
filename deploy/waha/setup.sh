#!/usr/bin/env bash
# ===========================================================================
# setup_waha_hetzner.sh — Provisiona WAHA + Caddy + Audio Proxy en un VPS Ubuntu
# ---------------------------------------------------------------------------
# Uso:
#   1. Crea un VPS Ubuntu 22.04/24.04 (tipo CX22 o similar).
#   2. Apunta un subdominio a la IP del VPS (DNS A):  waha.tudominio.com -> IP
#   3. Conéctate por SSH y ejecuta:
#        sudo bash setup.sh waha.tudominio.com https://tu-plataforma.vercel.app
#
# Al terminar imprime la WAHA_API_KEY generada: cópiala para Vercel.
# ===========================================================================
set -euo pipefail

DOMAIN="${1:-}"
GENIA_BACKEND_URL="${2:-}"

if [ -z "$DOMAIN" ]; then
  echo "❌ Uso: sudo bash setup.sh waha.tudominio.com [https://tu-plataforma.vercel.app]"
  exit 1
fi

if [ -z "$GENIA_BACKEND_URL" ]; then
  GENIA_BACKEND_URL="https://plataforma-genia.vercel.app"
  echo "ℹ️ No se especificó URL de backend de Genia. Usando por defecto: $GENIA_BACKEND_URL"
fi

echo "🚀 Instalando Docker en el VPS..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg ufw openssl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg || true
chmod a+r /etc/apt/keyrings/docker.gpg || true
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "📁 Preparando /opt/waha..."
mkdir -p /opt/waha
cd /opt/waha

# Generar API key fuerte si no existe
WAHA_API_KEY=$(openssl rand -hex 24)
echo "🔑 WAHA_API_KEY generada: $WAHA_API_KEY"

# Escribir .env (Docker Compose lo lee automáticamente)
cat > .env <<EOF
WAHA_API_KEY=$WAHA_API_KEY
WAHA_PORT=3000
GENIA_BACKEND_URL=$GENIA_BACKEND_URL
EOF

# Escribir Caddyfile con el dominio y redirecciones
cat > Caddyfile <<EOF
$DOMAIN {
    # Redirigir webhooks de WhatsApp al Proxy de Audio
    reverse_proxy /webhook/waha/* audio-proxy:4000

    # Redirigir el resto del tráfico REST directamente a WAHA
    reverse_proxy * waha:3000
}
EOF

# Escribir Dockerfile.proxy
cat > Dockerfile.proxy <<'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn httpx
COPY audio_proxy.py .
EXPOSE 4000
CMD ["uvicorn", "audio_proxy:app", "--host", "0.0.0.0", "--port", "4000"]
EOF

# Escribir audio_proxy.py
cat > audio_proxy.py <<'EOF'
import os
import logging
import base64
import httpx
from fastapi import FastAPI, Request, Response, status

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audio_proxy")

app = FastAPI(title="Genia Audio Proxy")

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
            internal_media_url = media_url.replace("localhost:3000", "waha:3000").replace("127.0.0.1:3000", "waha:3000")
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
EOF

# Escribir docker-compose.yml
cat > docker-compose.yml <<'EOF'
services:
  waha:
    image: devlikeapro/waha:latest
    restart: unless-stopped
    expose:
      - "3000"
    environment:
      - WAHA_API_KEY=${WAHA_API_KEY:-}
      - WAHA_SWAGGER_ENABLED=true
      - WAHA_FILES_LIMIT=100mb
      - WHATSAPP_RESTART_ON_AUTH_FAIL=false
      - WAHA_SESSION_PHONE_NOT_FOUND=keep
    volumes:
      - waha-data:/app/.sessions
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/api/version"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

  audio-proxy:
    build:
      context: .
      dockerfile: Dockerfile.proxy
    restart: unless-stopped
    expose:
      - "4000"
    environment:
      - GENIA_BACKEND_URL=${GENIA_BACKEND_URL}
      - WAHA_API_KEY=${WAHA_API_KEY}
      - WAHA_LOCAL_URL=http://waha:3000
    depends_on:
      - waha

  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    depends_on:
      - waha
      - audio-proxy

volumes:
  waha-data:
  caddy-data:
  caddy-config:
EOF

echo "🔥 Configurando firewall (22, 80, 443)..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "🐳 Levantando WAHA + Caddy + Audio Proxy..."
docker compose up -d --build

echo ""
echo "✅ Listo. Espera ~20s a que Caddy obtenga el certificado HTTPS."
echo "   Comprueba:  curl https://$DOMAIN/api/version  (con header X-Api-Key)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " COPIA ESTOS VALORES EN VERCEL (Settings > Environment Variables):"
echo ""
echo "   WAHA_API_URL = https://$DOMAIN"
# Imprimir valores
echo "   WAHA_API_KEY = $WAHA_API_KEY"
echo ""
echo " Luego Redeploy en Vercel y conecta el agente desde el dashboard (pestaña WAHA)."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
