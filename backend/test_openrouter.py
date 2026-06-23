"""
Script de pruebas para verificar la integración de OpenRouter y el registro de consumo de tokens.
"""

import sys
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal, init_db
from models.agent import Agent
from models.agent_usage import AgentUsage
from models.conversation import Conversation, Message

# Usar context manager de TestClient para ejecutar lifespan y levantar base de datos
def clean_database():
    """Limpia registros de prueba de la base de datos."""
    db = SessionLocal()
    try:
        # Eliminar registros de consumo de prueba
        db.query(AgentUsage).delete()
        # Eliminar mensajes
        db.query(Message).delete()
        # Eliminar conversaciones
        db.query(Conversation).delete()
        # Eliminar agentes de prueba
        db.query(Agent).filter(Agent.name == "OpenRouter Bot Test").delete()
        db.commit()
        print("[CLEAN] Base de datos limpia.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error limpiando base de datos: {e}")
    finally:
        db.close()

def run_openrouter_test():
    print("\n[START] Iniciando Pruebas de OpenRouter y Consumo de Tokens...\n")

    # Usar context manager para levantar el lifespan y base de datos
    with TestClient(app) as client:
        # 1. Crear un agente con OpenRouter
        print("--- 1. Creando Agente con OpenRouter ---")
        agent_payload = {
            "name": "OpenRouter Bot Test",
            "description": "Agente de prueba para OpenRouter",
            "system_prompt": "Eres un asistente de prueba rápido. Responde con la palabra exacta '¡Hola!' y nada más.",
            "provider": "openrouter",
            "model": "deepseek/deepseek-chat",
            "temperature": 0.1,
            "max_tokens": 50,
            "custom_fields": [],
            "channels": ["web"]
        }

        response = client.post("/api/agents/", json=agent_payload)
        assert response.status_code == 201, f"Error creando agente: {response.text}"
        agent_data = response.json()
        agent_id = agent_data["id"]
        print(f"Agente creado con ID: {agent_id} y proveedor: {agent_data['provider']} (modelo: {agent_data['model']})")

        # 2. Enviar mensaje de chat
        print("\n--- 2. Probando Chat Sandbox ---")
        chat_payload = {
            "agent_id": agent_id,
            "message": "Salúdame por favor."
        }
        response = client.post("/api/chat/", json=chat_payload)
        assert response.status_code == 200, f"Error en chat: {response.text}"
        chat_res = response.json()
        reply = chat_res["reply"]
        conversation_id = chat_res["conversation_id"]
        print(f"Conversación ID: {conversation_id}")
        print(f"Respuesta del Agente: '{reply}'")
        assert "Hola" in reply or "hola" in reply.lower() or "¡Hola!" in reply, f"Respuesta inesperada: {reply}"

        # 3. Consultar Consumo de Tokens
        print("\n--- 3. Verificando Registro de Consumo ---")
        response = client.get(f"/api/agents/{agent_id}/usage")
        assert response.status_code == 200, f"Error obteniendo consumo: {response.text}"
        usages = response.json()
        print(f"Consumo de tokens recuperado: {usages}")
        
        assert len(usages) > 0, "No se registró ningún consumo para el agente."
        usage = usages[0]
        
        assert usage["model"] == "deepseek/deepseek-chat", f"Modelo incorrecto en consumo: {usage['model']}"
        assert usage["prompt_tokens"] > 0, f"Prompt tokens debería ser > 0, obtenido: {usage['prompt_tokens']}"
        assert usage["completion_tokens"] > 0, f"Completion tokens debería ser > 0, obtenido: {usage['completion_tokens']}"
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"], "El total_tokens no coincide con la suma."
        assert usage["cost"] > 0.0, f"El costo calculado debería ser > 0.0, obtenido: {usage['cost']}"
        
        print(f"[OK] Consumo validado con éxito:")
        print(f"  Modelo: {usage['model']}")
        print(f"  Prompt tokens: {usage['prompt_tokens']}")
        print(f"  Completion tokens: {usage['completion_tokens']}")
        print(f"  Total tokens: {usage['total_tokens']}")
        print(f"  Costo estimado: USD {usage['cost']:.6f}")

        print("\n[OK] ¡LAS PRUEBAS DE OPENROUTER Y CONSUMO PASARON EXITOSAMENTE!\n")

if __name__ == "__main__":
    try:
        init_db()
        clean_database()
        run_openrouter_test()
    except AssertionError as ae:
        print(f"\n[FAIL] FALLÓ LA PRUEBA: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR INESPERADO: {e}")
        sys.exit(1)
    finally:
        clean_database()
