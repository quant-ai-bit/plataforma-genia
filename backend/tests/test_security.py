"""
Pruebas automatizadas de seguridad:
- Endpoints de cron protegidos con CRON_SECRET.
- Webhooks de WAHA protegidos con API Key.
- Endpoints sensibles no expuestos.
- Aislamiento multi-tenant por agente (require_agent_access).
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from database import get_db
from models.agent import Agent
from models.user_account import UserAccount
from services.auth_service import get_current_user
from config import settings


def test_cron_endpoint_without_secret(client):
    """Verifica que /waha/monitor rechaza llamadas si no viene el CRON_SECRET."""
    settings.cron_secret = "super_secret_cron_123"
    response = client.post("/api/whatsapp/waha/monitor")
    assert response.status_code == 401


def test_cron_endpoint_with_valid_secret(client):
    """Verifica que /waha/monitor acepta llamadas con el CRON_SECRET correcto."""
    settings.cron_secret = "super_secret_cron_123"
    headers = {"Authorization": "Bearer super_secret_cron_123"}
    response = client.post("/api/whatsapp/waha/monitor", headers=headers)
    assert response.status_code in (200, 500)  # Puede dar 200 o fallo interno si WAHA está mockeado, pero NO 401


def test_check_inactivity_without_secret(client):
    """Verifica que /check-inactivity rechaza llamadas sin CRON_SECRET."""
    settings.cron_secret = "super_secret_cron_123"
    response = client.get("/api/whatsapp/check-inactivity")
    assert response.status_code == 401


def test_waha_ai_test_removed(client):
    """Verifica que el endpoint inseguro ai-test ya no existe (404/405/400)."""
    response = client.post("/api/whatsapp/webhook/waha/ai-test")
    # Al estar eliminado, FastAPI rutea a webhook/waha/{agent_id} esperando un payload de webhook
    # o retorna 404/400 pero nunca ejecuta la lógica de depuración de prompts
    assert response.status_code in (400, 404, 405)


def test_waha_diag_removed(client):
    """Verifica que el endpoint inseguro diag ya no existe (404/405)."""
    response = client.get("/api/whatsapp/webhook/waha/diag")
    assert response.status_code in (404, 405)


def test_public_health_check_safe(client):
    """Verifica que /api/whatsapp/health responde 200 sin filtrar nombres de sesiones privadas."""
    response = client.get("/api/whatsapp/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "list" not in data  # Las sesiones de clientes ya no se exponen públicamente


def test_waha_webhook_enforce_mode(client):
    """Verifica que el webhook de WAHA rechaza peticiones sin clave cuando está en enforce."""
    settings.waha_api_key = "waha_secret_abc"
    settings.waha_webhook_auth_mode = "enforce"
    
    # Sin clave
    response = client.post("/api/whatsapp/webhook/waha/agent1", json={"event": "message"})
    assert response.status_code == 401

    # Con clave correcta
    headers = {"X-Api-Key": "waha_secret_abc"}
    response_valid = client.post("/api/whatsapp/webhook/waha/agent1", json={"event": "message"}, headers=headers)
    assert response_valid.status_code != 401  # Pasa la capa de autenticación del webhook


def test_require_agent_access_isolation(db_session, client):
    """Verifica que un usuario cliente regular no puede acceder a contactos de otro agente."""
    # Crear agente A y agente B con campos obligatorios
    agent_a = Agent(id="agent_a_123", name="Agente Cliente A", system_prompt="Prompt A", status="active")
    agent_b = Agent(id="agent_b_456", name="Agente Cliente B", system_prompt="Prompt B", status="active")
    db_session.add_all([agent_a, agent_b])

    # Usuario asignado solo al agente A
    user_a = UserAccount(
        id="user_a_uuid",
        email="cliente_a@empresa.com",
        role="user",
        status="active",
        assigned_agent_id="agent_a_123",
    )
    db_session.add(user_a)
    db_session.commit()

    # Sobrescribir autenticación simulando la sesión de usuario A
    app.dependency_overrides[get_current_user] = lambda: {"id": "user_a_uuid", "email": "cliente_a@empresa.com"}

    try:
        # Intentar acceder a los contactos del agente B (debe dar 403 Forbidden)
        response_forbidden = client.get("/api/agents/agent_b_456/contacts")
        assert response_forbidden.status_code == 403

        # Acceder a su propio agente A (debe dar 200 OK)
        response_ok = client.get("/api/agents/agent_a_123/contacts")
        assert response_ok.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
