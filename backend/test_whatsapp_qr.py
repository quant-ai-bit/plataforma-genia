"""
Prueba unitaria e integración para verificar la conexión de WhatsApp Dual (Meta y QR Code).
"""

import sys
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models.agent import Agent
from models.conversation import Conversation
from models.lead import Lead
from models.conversation import Message

client = TestClient(app)


def test_whatsapp_qr_flow():
    print("\n[START] Iniciando Pruebas de WhatsApp QR Integration...")

    # 1. Crear un Agente de prueba
    agent_payload = {
        "name": "QR Test Agent",
        "description": "Agente para probar flujo QR",
        "system_prompt": "Eres un asistente de prueba. Responde 'OK' a todo.",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.5,
        "max_tokens": 512,
        "custom_fields": [],
        "channels": ["web"]
    }
    
    response = client.post("/api/agents/", json=agent_payload)
    assert response.status_code == 201, f"Error creando agente: {response.text}"
    agent_data = response.json()
    agent_id = agent_data["id"]
    print(f"[OK] Agente de prueba creado con ID: {agent_id}")

    try:
        # 2. Verificar estado inicial de WhatsApp (debe ser meta_cloud y desconectado)
        response = client.get(f"/api/whatsapp/{agent_id}/status")
        assert response.status_code == 200, f"Error obteniendo status: {response.text}"
        status_data = response.json()
        assert status_data["connected"] is False
        assert status_data["whatsapp_provider"] == "meta_cloud"
        print("[OK] Estado inicial verificado correctamente (Meta Cloud, desconectado).")

        # 3. Cambiar proveedor a QR Code
        response = client.post(f"/api/whatsapp/{agent_id}/provider", json={"provider": "qr_code"})
        assert response.status_code == 200, f"Error cambiando proveedor: {response.text}"
        provider_data = response.json()
        assert provider_data["whatsapp_provider"] == "qr_code"
        print("[OK] Proveedor de WhatsApp cambiado a 'qr_code' exitosamente.")

        # 4. Conectar QR (Generar instancia)
        response = client.post(f"/api/whatsapp/{agent_id}/qr/connect")
        assert response.status_code == 200, f"Error generando QR: {response.text}"
        connect_data = response.json()
        assert connect_data["status"] == "connecting"
        assert "qr_code" in connect_data
        assert connect_data["qr_code"] is not None
        print("[OK] Instancia QR generada exitosamente. QR recibido en base64.")

        # 5. Verificar status (debe estar connecting / qr_connected False en mock)
        response = client.get(f"/api/whatsapp/{agent_id}/status")
        assert response.status_code == 200, f"Error obteniendo status QR: {response.text}"
        status_data = response.json()
        assert status_data["whatsapp_provider"] == "qr_code"
        assert status_data["connected"] is False
        assert status_data["whatsapp_qr_connected"] is False
        print("[OK] Status QR intermedio verificado correctamente.")

        # 6. Simular escaneo de QR
        response = client.post(f"/api/whatsapp/{agent_id}/qr/simulate-scan")
        assert response.status_code == 200, f"Error simulando escaneo: {response.text}"
        scan_data = response.json()
        assert scan_data["status"] == "connected"
        print("[OK] Simulación de escaneo QR realizada con éxito.")

        # 7. Verificar status post-escaneo (debe ser connected y qr_connected True)
        response = client.get(f"/api/whatsapp/{agent_id}/status")
        assert response.status_code == 200, f"Error obteniendo status post-escaneo: {response.text}"
        status_data = response.json()
        assert status_data["connected"] is True
        assert status_data["whatsapp_qr_connected"] is True
        assert status_data["phone_number"] == "573103125460"
        print("[OK] Estado final de WhatsApp QR verificado como CONECTADO.")

        # 8. Simular webhook de mensaje entrante de Evolution API
        webhook_payload = {
            "event": "messages.upsert",
            "instance": f"genia_agent_{agent_id}",
            "data": {
                "key": {
                    "remoteJid": "573009999999@s.whatsapp.net",
                    "fromMe": False,
                    "id": "MOCK_MSG_12345"
                },
                "message": {
                    "conversation": "Hola, esto es una prueba."
                },
                "messageType": "conversation",
                "pushName": "Carlos QR Test"
            }
        }
        
        response = client.post(f"/api/whatsapp/webhook/qr/{agent_id}", json=webhook_payload)
        assert response.status_code == 200, f"Error en webhook QR: {response.text}"
        assert response.json()["status"] == "accepted"
        print("[OK] Webhook de mensaje QR recibido y procesado correctamente.")

        # 9. Desconectar QR
        response = client.post(f"/api/whatsapp/{agent_id}/qr/disconnect")
        assert response.status_code == 200, f"Error desconectando QR: {response.text}"
        disconnect_data = response.json()
        assert disconnect_data["status"] == "disconnected"
        print("[OK] Desconexión QR completada exitosamente.")

        # 10. Confirmar status final desconectado
        response = client.get(f"/api/whatsapp/{agent_id}/status")
        assert response.status_code == 200, f"Error en status final: {response.text}"
        status_data = response.json()
        assert status_data["connected"] is False
        assert status_data["whatsapp_qr_connected"] is False
        print("[OK] Estado final desconectado confirmado.")

    finally:
        # Limpieza
        db = SessionLocal()
        try:
            db.query(Message).delete()
            db.query(Conversation).delete()
            db.query(Agent).filter(Agent.id == agent_id).delete()
            db.commit()
            print("[CLEAN] Datos de prueba de WhatsApp QR eliminados.")
        except Exception as e:
            db.rollback()
            print(f"[ERROR] Error en limpieza: {e}")
        finally:
            db.close()

    print("\n[SUCCESS] Todas las pruebas de WhatsApp QR pasaron exitosamente!\n")


if __name__ == "__main__":
    test_whatsapp_qr_flow()
