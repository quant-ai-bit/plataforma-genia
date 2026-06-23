"""
Script de Pruebas de Integración E2E para PLATAFORMA GENIA.

Simula el flujo completo de la Fase 1 sin emojis para evitar problemas de encoding.
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


def clean_database():
    """Limpia registros de prueba anteriores de la base de datos."""
    db = SessionLocal()
    try:
        # Eliminar leads de prueba
        db.query(Lead).delete()
        # Eliminar mensajes
        db.query(Message).delete()
        # Eliminar conversaciones
        db.query(Conversation).delete()
        # Eliminar agentes de prueba creados
        db.query(Agent).filter(Agent.name == "Genia Bot Test").delete()
        db.commit()
        print("[CLEAN] Base de datos limpiada para la prueba.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error limpiando base de datos: {e}")
    finally:
        db.close()


def run_e2e_test():
    print("\n[START] Iniciando Pruebas de Integración E2E...\n")

    # --- 1. Health Check ---
    print("--- 1. Probando Health Check ---")
    response = client.get("/")
    assert response.status_code == 200, f"Error: {response.text}"
    print(f"Health Check OK: {response.json()}")

    # --- 2. Modelos Disponibles ---
    print("\n--- 2. Probando Obtención de Modelos ---")
    response = client.get("/api/models")
    assert response.status_code == 200, f"Error: {response.text}"
    models_data = response.json()
    print(f"Modelos de Groq: {models_data.get('groq')}")
    print(f"Modelos de Gemini: {models_data.get('gemini')}")
    assert "llama-3.3-70b-versatile" in models_data.get("groq")

    # --- 3. Crear Agente ---
    print("\n--- 3. Creando Agente de IA para Captura de Leads ---")
    agent_payload = {
        "name": "Genia Bot Test",
        "description": "Agente comercial para pruebas de captura de leads",
        "system_prompt": (
            "Eres un agente comercial experto en soluciones de IA de la agencia GENIA. "
            "Tu objetivo es conversar con el usuario de manera amable, pero DEBES capturar "
            "los siguientes datos obligatorios de inmediato: nombre, correo electrónico (email), "
            "su tipo de negocio (business_type) y la cantidad de empleados (num_employees). "
            "Tan pronto como el usuario te provea esta información (o parte de ella), debes llamar "
            "inmediatamente a la función save_lead_info para registrar sus datos. "
            "Sé conciso y ve al grano en tus respuestas."
        ),
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.2,  # Baja temperatura para consistencia
        "max_tokens": 1024,
        "custom_fields": [
            {
                "key": "email",
                "label": "Correo electrónico",
                "type": "string",
                "required": True
            },
            {
                "key": "business_type",
                "label": "Tipo de negocio",
                "type": "string",
                "required": True
            },
            {
                "key": "num_employees",
                "label": "Número de empleados",
                "type": "integer",
                "required": False
            }
        ],
        "channels": ["web"]
    }

    response = client.post("/api/agents/", json=agent_payload)
    assert response.status_code == 201, f"Error: {response.text}"
    agent_data = response.json()
    agent_id = agent_data["id"]
    print(f"Agente creado exitosamente con ID: {agent_id}")

    # --- 4. Listar Agentes ---
    print("\n--- 4. Listando Agentes ---")
    response = client.get("/api/agents/")
    assert response.status_code == 200, f"Error: {response.text}"
    agents_list = response.json()
    assert any(a["id"] == agent_id for a in agents_list)
    print(f"Listado exitoso, cantidad de agentes: {len(agents_list)}")

    # --- 5. Chat Sandbox - Interacción 1 (Saludo) ---
    print("\n--- 5. Chat Sandbox: Envío de Saludo ---")
    chat_payload_1 = {
        "agent_id": agent_id,
        "message": "Hola, me interesa automatizar los procesos de mi empresa con IA."
    }
    response = client.post("/api/chat/", json=chat_payload_1)
    assert response.status_code == 200, f"Error: {response.text}"
    chat_res_1 = response.json()
    conversation_id = chat_res_1["conversation_id"]
    reply_1 = chat_res_1["reply"]
    print(f"Conversación iniciada con ID: {conversation_id}")
    print(f"Respuesta del Agente:\n> {reply_1}\n")

    # --- 6. Chat Sandbox - Interacción 2 (Proveer datos) ---
    print("--- 6. Chat Sandbox: Proveyendo datos para captura de Lead ---")
    chat_payload_2 = {
        "agent_id": agent_id,
        "message": (
            "Hola! Claro, me llamo Carlos Gómez, mi correo es carlos@inmobiliaria.xyz, "
            "tengo una constructora e inmobiliaria, y somos 25 personas trabajando."
        ),
        "conversation_id": conversation_id
    }
    response = client.post("/api/chat/", json=chat_payload_2)
    assert response.status_code == 200, f"Error: {response.text}"
    chat_res_2 = response.json()
    reply_2 = chat_res_2["reply"]
    print(f"Respuesta del Agente tras recibir datos:\n> {reply_2}\n")

    # --- 7. Verificar Captura de Lead ---
    print("--- 7. Verificando Lead capturado en la Base de Datos ---")
    response = client.get("/api/leads/")
    assert response.status_code == 200, f"Error: {response.text}"
    leads = response.json()
    
    # Buscar el lead de Carlos Gómez
    carlos_lead = None
    for lead in leads:
        if lead["conversation_id"] == conversation_id:
            carlos_lead = lead
            break
            
    assert carlos_lead is not None, "Error: No se guardó el lead para esta conversación."
    print("Lead encontrado en base de datos:")
    print(f"  Nombre: {carlos_lead['name']}")
    print(f"  Email: {carlos_lead['email']}")
    print(f"  Campos personalizados (custom_data): {carlos_lead['custom_data']}")
    
    assert carlos_lead["name"] == "Carlos Gómez"
    assert carlos_lead["email"] == "carlos@inmobiliaria.xyz"
    # Campos dinámicos
    assert "business_type" in carlos_lead["custom_data"]
    
    print("[OK] Lead verificado exitosamente.")

    # --- 8. Verificar Historial de Conversación ---
    print("\n--- 8. Verificando Historial de Conversación ---")
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 200, f"Error: {response.text}"
    conv_detail = response.json()
    print(f"Conversación con {conv_detail['contact_name']} / {conv_detail['contact_phone']}")
    print(f"Total de mensajes en la transcripción: {len(conv_detail['messages'])}")
    for msg in conv_detail["messages"]:
        print(f"  [{msg['role'].upper()}]: {msg['content']}")
    
    assert len(conv_detail["messages"]) >= 4, "Debería haber al menos 4 mensajes (User, Assistant, User, Assistant)."

    # --- 9. Métricas del Dashboard ---
    print("\n--- 9. Probando Obtención de Métricas del Dashboard ---")
    response = client.get("/api/dashboard/metrics")
    assert response.status_code == 200, f"Error: {response.text}"
    metrics = response.json()
    print("Métricas consolidadas:")
    print(f"  Total Agentes: {metrics['total_agents']}")
    print(f"  Total Conversaciones: {metrics['total_conversations']}")
    print(f"  Total Leads: {metrics['total_leads']}")
    print(f"  Conversaciones por estado: {metrics['conversations_by_status']}")
    print(f"  Historial de leads (últimos 7 días): {metrics['leads_history']}")
    print(f"  Leads recientes: {len(metrics['recent_leads'])}")
    
    assert metrics["total_agents"] >= 1
    assert metrics["total_conversations"] >= 1
    assert metrics["total_leads"] >= 1

    print("\n[OK] ¡TODAS LAS PRUEBAS DE INTEGRACIÓN PASARON EXITOSAMENTE!\n")


if __name__ == "__main__":
    try:
        clean_database()
        run_e2e_test()
    except AssertionError as ae:
        print(f"\n[FAIL] FALLÓ LA PRUEBA: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR INESPERADO: {e}")
        sys.exit(1)
    finally:
        clean_database()
