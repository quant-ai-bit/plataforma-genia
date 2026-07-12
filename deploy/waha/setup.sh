#!/usr/bin/env bash
# ===========================================================================
# setup_waha_hetzner.sh — Provisiona WAHA + Caddy en un VPS Ubuntu (Hetzner)
# ---------------------------------------------------------------------------
# Uso:
#   1. Crea un VPS Ubuntu 22.04/24.04 en Hetzner (tipo CX22 o similar, ~$5/mes).
#   2. Apunta un subdominio a la IP del VPS (DNS A):  waha.tudominio.com -> IP
#   3. Conéctate por SSH y ejecuta:
#        bash <(curl -fsSL https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/deploy/waha/setup.sh) waha.tudominio.com
#      O bien: sube este script al VPS y corre:  sudo bash setup.sh waha.tudominio.com
#
# Al terminar imprime la WAHA_API_KEY generada: cópiala para Vercel.
# ===========================================================================
set -euo pipefail

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  echo "❌ Uso: sudo bash setup.sh waha.tudominio.com"
  exit 1
fi

echo "🚀 Instalando Docker en el VPS..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg ufw
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
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
EOF

# Escribir Caddyfile con el dominio
cat > Caddyfile <<EOF
$DOMAIN {
    reverse_proxy waha:3000
}
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

echo "🐳 Levantando WAHA + Caddy..."
docker compose up -d

echo ""
echo "✅ Listo. Espera ~20s a que Caddy obtenga el certificado HTTPS."
echo "   Comprueba:  curl https://$DOMAIN/api/version  (con header X-Api-Key)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " COPIA ESTOS VALORES EN VERCEL (Settings > Environment Variables):"
echo ""
echo "   WAHA_API_URL = https://$DOMAIN"
echo "   WAHA_API_KEY = $WAHA_API_KEY"
echo ""
echo " Luego Redeploy en Vercel y conecta el agente desde el dashboard (pestaña WAHA)."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
