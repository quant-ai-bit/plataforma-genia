"""
Pruebas unitarias para validar la integración de Google Calendar y multi-proveedor STT.
"""

import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models.agent import Agent
from services.auth_service import get_current_user
from services import encryption_service

client = TestClient(app)

# Bypass de autenticación para pruebas
app.dependency_overrides[get_current_user] = lambda: {
    "id": "local_dev_user",
    "email": "test@test.com",
    "name": "Usuario Test",
}

def clean_db():
    db = SessionLocal()
    try:
        db.query(Agent).filter(Agent.name == "Agente Integraciones Test").delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error limpiando DB: {e}")
    finally:
        db.close()

def test_stt_and_calendar():
    print("\n=== INICIANDO PRUEBAS DE CALENDAR Y STT ===\n")
    
    # 1. Crear Agente con credenciales de Google Calendar, STT provider y Timezone
    print("1. Creando agente con campos de Calendar, STT y Timezone...")
    agent_payload = {
        "name": "Agente Integraciones Test",
        "description": "Agente de prueba para Google Calendar y STT configurable",
        "system_prompt": "Eres un asistente de reservas. Ayuda a agendar citas.",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.5,
        "max_tokens": 512,
        "custom_fields": [],
        "channels": ["web"],
        "google_calendar_client_id": "test-client-id-123",
        "google_calendar_client_secret": "test-client-secret-abc",
        "stt_provider": "deepgram",
        "timezone": "America/Mexico_City"
    }

    res = client.post("/api/agents/", json=agent_payload)
    assert res.status_code == 201, f"Error creando agente: {res.text}"
    agent_data = res.json()
    agent_id = agent_data["id"]
    
    assert agent_data["google_calendar_client_id"] == "test-client-id-123"
    assert agent_data["stt_provider"] == "deepgram"
    assert agent_data["timezone"] == "America/Mexico_City"
    print(f"Agente creado con éxito. ID: {agent_id}")

    # Verificar cifrado del client secret en la base de datos
    db = SessionLocal()
    agent_in_db = db.query(Agent).filter(Agent.id == agent_id).first()
    assert agent_in_db.google_calendar_client_secret is not None
    decrypted_secret = encryption_service.decrypt(agent_in_db.google_calendar_client_secret)
    assert decrypted_secret == "test-client-secret-abc"
    print("[OK] Cifrado Fernet de Google Calendar Client Secret validado correctamente en la BD.")
    db.close()

    # 2. Generar URL de Auth OAuth
    print("\n2. Probando obtencion de URL de OAuth...")
    auth_res = client.get(f"/api/calendar/{agent_id}/auth-url?base_url=http://localhost:3000")
    assert auth_res.status_code == 200, f"Error obteniendo auth URL: {auth_res.text}"
    auth_data = auth_res.json()
    assert "auth_url" in auth_data
    assert "accounts.google.com" in auth_data["auth_url"]
    assert f"state={agent_id}" in auth_data["auth_url"]
    print("[OK] URL de OAuth generada exitosamente:")
    print(f"  {auth_data['auth_url']}")

    # 3. Simular Callback de Google OAuth
    print("\n3. Probando callback de OAuth...")
    mock_credentials = MagicMock()
    mock_credentials.refresh_token = "mock-refresh-token-xyz"
    
    with patch("services.google_calendar_service.Flow.from_client_config") as mock_flow_class, \
         patch("services.google_calendar_service._get_user_email") as mock_email:
        
        mock_flow = MagicMock()
        mock_flow.credentials = mock_credentials
        mock_flow_class.return_value = mock_flow
        mock_email.return_value = "calendar-negocio@gmail.com"
        
        callback_res = client.get(f"/api/calendar/{agent_id}/callback?code=mock-auth-code-123&state={agent_id}")
        assert callback_res.status_code == 200
        assert "Google Calendar Conectado" in callback_res.text
        
    # Verificar base de datos después del callback
    db = SessionLocal()
    agent_in_db = db.query(Agent).filter(Agent.id == agent_id).first()
    assert agent_in_db.google_calendar_connected == True
    assert agent_in_db.google_calendar_email == "calendar-negocio@gmail.com"
    assert "google_calendar" in agent_in_db.channels
    print("[OK] Conexion establecida en DB y canal 'google_calendar' agregado exitosamente.")
    db.close()

    # 4. Consultar status
    print("\n4. Consultando estado de conexion...")
    status_res = client.get(f"/api/calendar/{agent_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["connected"] == True
    assert status_data["email"] == "calendar-negocio@gmail.com"
    print(f"[OK] Estado de conexion devuelto: {status_data}")

    # 5. Probar listado de proveedores STT
    print("\n5. Consultando proveedores de Voz a Texto (STT)...")
    stt_res = client.get("/api/calendar/stt-providers")
    assert stt_res.status_code == 200
    stt_data = stt_res.json()
    assert "providers" in stt_data
    providers = [p["id"] for p in stt_data["providers"]]
    assert "groq_whisper" in providers
    assert "deepgram" in providers
    assert "google_stt" in providers
    assert "openai_whisper" in providers
    print(f"[OK] Proveedores STT disponibles en API: {providers}")

    # 6. Desconectar Google Calendar
    print("\n6. Probando desconexion de Google Calendar...")
    disconnect_res = client.post(f"/api/calendar/{agent_id}/disconnect")
    assert disconnect_res.status_code == 200
    disconnect_data = disconnect_res.json()
    assert disconnect_data["status"] == "disconnected"
    
    db = SessionLocal()
    agent_in_db = db.query(Agent).filter(Agent.id == agent_id).first()
    assert agent_in_db.google_calendar_connected == False
    assert agent_in_db.google_calendar_email is None
    assert agent_in_db.google_calendar_refresh_token is None
    print("[OK] Desconexion de Google Calendar completada y tokens eliminados correctamente.")
    db.close()

    print("\n=== ¡TODAS LAS PRUEBAS DE CALENDAR Y STT PASARON EXITOSAMENTE! ===\n")

if __name__ == "__main__":
    try:
        clean_db()
        test_stt_and_calendar()
    finally:
        clean_db()
