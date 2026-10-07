"""
Script de Pruebas de Integración RAG para PLATAFORMA GENIA.

Verifica el flujo de la Fase 2:
1. Crea un agente.
2. Sube un documento de texto con políticas específicas.
3. Envía una consulta de chat que requiere dicha información y valida RAG.
4. Elimina el documento y verifica que el contexto ya no se recupere.
"""

import sys
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
from models.agent import Agent
from models.conversation import Conversation
from models.lead import Lead
from models.knowledge import KnowledgeDocument
from models.conversation import Message

client = TestClient(app)


def clean_database():
    """Limpia registros de prueba anteriores de la base de datos de manera aislada."""
    db = SessionLocal()
    try:
        # Buscar el agente de prueba
        test_agent = db.query(Agent).filter(Agent.name == "Genia RAG Bot Test").first()
        if test_agent:
            agent_id = test_agent.id
            # Eliminar leads de este agente
            db.query(Lead).filter(Lead.agent_id == agent_id).delete()
            
            # Eliminar mensajes de las conversaciones de este agente
            convs = db.query(Conversation).filter(Conversation.agent_id == agent_id).all()
            conv_ids = [c.id for c in convs]
            if conv_ids:
                db.query(Message).filter(Message.conversation_id.in_(conv_ids)).delete()
            
            # Eliminar conversaciones
            db.query(Conversation).filter(Conversation.agent_id == agent_id).delete()
            
            # Eliminar documentos de conocimiento de este agente
            db.query(KnowledgeDocument).filter(KnowledgeDocument.agent_id == agent_id).delete()
            
            # Eliminar al agente de prueba
            db.query(Agent).filter(Agent.id == agent_id).delete()
            
            db.commit()
            print("[CLEAN] Base de datos limpia (agente de prueba y sus datos eliminados).")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error limpiando base de datos: {e}")
    finally:
        db.close()


def run_rag_test():
    print("\n[START] Iniciando Pruebas de Integración RAG (Fase 2)...\n")

    # --- 1. Crear Agente ---
    print("--- 1. Creando Agente de Prueba ---")
    agent_payload = {
        "name": "Genia RAG Bot Test",
        "description": "Agente para pruebas de búsqueda semántica y RAG",
        "system_prompt": (
            "Eres un asistente de soporte de PLATAFORMA GENIA. Tu deber es ayudar a los clientes "
            "basándote exclusivamente en el [CONTEXTO DE NEGOCIO] provisto. Si la información no está "
            "en el contexto, responde de manera amable indicando que no posees esa información en este momento."
        ),
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.0,  # Temperatura 0 para máxima fidelidad al contexto
        "max_tokens": 1024,
        "custom_fields": [],
        "channels": ["web"]
    }

    response = client.post("/api/agents/", json=agent_payload)
    assert response.status_code == 201, f"Error: {response.text}"
    agent_id = response.json()["id"]
    print(f"Agente creado con ID: {agent_id}")

    # --- 2. Subir Documento de Conocimiento ---
    print("\n--- 2. Subiendo Documento de Políticas de Reembolso ---")
    doc_content = (
        "POLITICA DE REEMBOLSOS Y DEVOLUCIONES DE GENIA:\n"
        "1. Los clientes pueden solicitar la devolución total de su suscripción de software "
        "dentro de los primeros 14 días naturales después de la compra inicial.\n"
        "2. Para tramitar cualquier reembolso, el usuario debe enviar un correo a reembolsos@geniasoftware.io "
        "indicando su ID de cliente y el motivo de la cancelación.\n"
        "3. Las licencias corporativas personalizadas no son reembolsables bajo ninguna circunstancia."
    )
    
    file_payload = {
        "file": ("politica_reembolsos.txt", doc_content.encode("utf-8"), "text/plain")
    }

    response = client.post(f"/api/agents/{agent_id}/documents", files=file_payload)
    assert response.status_code == 201, f"Error: {response.text}"
    doc_data = response.json()
    doc_id = doc_data["id"]
    print(f"Documento subido exitosamente. ID: {doc_id}, Chunks generados: {doc_data['chunk_count']}")
    assert doc_data["chunk_count"] > 0

    # --- 3. Listar Documentos ---
    print("\n--- 3. Verificando Listado de Documentos del Agente ---")
    response = client.get(f"/api/agents/{agent_id}/documents")
    assert response.status_code == 200, f"Error: {response.text}"
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id
    print("Documento verificado en la lista.")

    # --- 4. Chat con RAG (Preguntar sobre la política de reembolso) ---
    print("\n--- 4. Chat Sandbox: Preguntando sobre Políticas de Reembolso ---")
    chat_payload_1 = {
        "agent_id": agent_id,
        "message": "¿Cuál es el correo para solicitar un reembolso y cuántos días tengo?"
    }
    response = client.post("/api/chat/", json=chat_payload_1)
    assert response.status_code == 200, f"Error: {response.text}"
    chat_res_1 = response.json()
    reply_1 = chat_res_1["reply"]
    print(f"Respuesta del Agente (Con RAG):\n> {reply_1}\n")
    
    # Validar que la respuesta contiene los datos clave del documento cargado
    assert "reembolsos@geniasoftware.io" in reply_1.lower() or "reembolsos" in reply_1.lower()
    assert "14" in reply_1
    print("[OK] RAG funcionando correctamente. El agente respondió usando el contexto de ChromaDB.")

    # --- 5. Eliminar el Documento ---
    print("\n--- 5. Eliminando el Documento de Conocimiento ---")
    response = client.delete(f"/api/documents/{doc_id}")
    assert response.status_code == 200, f"Error: {response.text}"
    print("Documento eliminado de SQL y ChromaDB.")

    # --- 6. Verificar que la lista de documentos está vacía ---
    response = client.get(f"/api/agents/{agent_id}/documents")
    assert response.status_code == 200
    assert len(response.json()) == 0
    print("Listado de documentos del agente vacío, verificado.")

    # --- 7. Chat de nuevo (Sin RAG, la información ya no existe) ---
    print("\n--- 6. Chat Sandbox: Preguntando de nuevo tras eliminar documento ---")
    chat_payload_2 = {
        "agent_id": agent_id,
        "message": "¿Cuál es el correo para solicitar un reembolso y cuántos días tengo?",
        "conversation_id": chat_res_1["conversation_id"]
    }
    response = client.post("/api/chat/", json=chat_payload_2)
    assert response.status_code == 200, f"Error: {response.text}"
    reply_2 = response.json()["reply"]
    print(f"Respuesta del Agente (Sin RAG):\n> {reply_2}\n")
    
    # El agente no debería poder dar la información exacta de reembolsos@geniasoftware.io ni los 14 días
    # ya que ya no está en el contexto. Debe decir que no sabe o dar una respuesta genérica.
    assert "reembolsos@geniasoftware.io" not in reply_2.lower()
    print("[OK] Verificado: El agente ya no tiene acceso a la información eliminada.")

    print("\n[OK] ¡TODAS LAS PRUEBAS DE INTEGRACIÓN RAG PASARON EXITOSAMENTE!\n")


if __name__ == "__main__":
    try:
        clean_database()
        run_rag_test()
    except AssertionError as ae:
        print(f"\n[FAIL] FALLÓ LA PRUEBA RAG: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR INESPERADO: {e}")
        sys.exit(1)
    finally:
        clean_database()
