"""
Script de pruebas para verificar el endpoint de edición de documentos de conocimiento.
"""

import sys
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal, init_db
from models.agent import Agent
from models.knowledge import KnowledgeDocument
from services.knowledge_service import retrieve_context

client = TestClient(app)

def clean_database():
    """Limpia registros de prueba de la base de datos."""
    db = SessionLocal()
    try:
        # Eliminar documentos de prueba
        db.query(KnowledgeDocument).filter(KnowledgeDocument.filename.like("Test Document%")).delete()
        # Eliminar agentes de prueba
        db.query(Agent).filter(Agent.name == "KB Update Bot Test").delete()
        db.commit()
        print("[CLEAN] Base de datos limpia.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error limpiando base de datos: {e}")
    finally:
        db.close()

def run_kb_update_test():
    print("\n[START] Iniciando Pruebas de Actualización de Documentos RAG...\n")

    with TestClient(app) as client:
        # 1. Crear un agente
        print("--- 1. Creando Agente de Prueba ---")
        agent_payload = {
            "name": "KB Update Bot Test",
            "description": "Agente para probar edición de RAG",
            "system_prompt": "Eres un asistente de soporte.",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.5,
            "max_tokens": 100,
            "custom_fields": [],
            "channels": ["web"]
        }
        response = client.post("/api/agents/", json=agent_payload)
        assert response.status_code == 201, f"Error: {response.text}"
        agent_data = response.json()
        agent_id = agent_data["id"]
        print(f"Agente creado con ID: {agent_id}")

        # 2. Agregar documento de texto manual
        print("\n--- 2. Guardando Documento de Conocimiento Inicial ---")
        doc_payload_1 = {
            "title": "Test Document",
            "content": "La política de reembolso de Genia permite cancelaciones gratuitas hasta 24 horas antes."
        }
        response = client.post(f"/api/agents/{agent_id}/documents/text", json=doc_payload_1)
        assert response.status_code == 201, f"Error: {response.text}"
        doc_data = response.json()
        doc_id = doc_data["id"]
        print(f"Documento creado con ID: {doc_id}, Filename: {doc_data['filename']}")

        # 2.5 Verificar que la consulta semántica inicial recupera "24 horas"
        initial_context = retrieve_context(agent_id=agent_id, query="politica de cancelacion gratis")
        print(f"Contexto semántico inicial recuperado:\n> {initial_context}")
        assert "24 horas" in initial_context, "El contexto inicial debería indicar 24 horas."

        # 3. Editar el documento de conocimiento
        print("\n--- 3. Editando Documento de Conocimiento (Cambiando a 48 horas) ---")
        doc_payload_2 = {
            "title": "Test Document Modified",
            "content": "La política de reembolso de Genia permite cancelaciones gratuitas hasta 48 horas antes."
        }
        response = client.put(f"/api/documents/{doc_id}", json=doc_payload_2)
        assert response.status_code == 200, f"Error: {response.text}"
        updated_doc_data = response.json()
        print(f"Documento actualizado: Filename: {updated_doc_data['filename']}")
        assert updated_doc_data["filename"] == "Test Document Modified.txt"

        # 4. Verificar que la base vectorial y recuperación semántica devuelven el nuevo contenido
        print("\n--- 4. Verificando que la base vectorial se haya re-indexado correctamente ---")
        updated_context = retrieve_context(agent_id=agent_id, query="politica de cancelacion gratis")
        print(f"Nuevo contexto semántico recuperado:\n> {updated_context}")
        
        assert "48 horas" in updated_context, "El contexto actualizado debería reflejar 48 horas."
        assert "24 horas" not in updated_context, "El contexto actualizado NO debería contener el valor antiguo de 24 horas."
        
        print("[OK] Base vectorial y base de datos SQL actualizadas e indexadas correctamente.")

        # 5. Obtener detalle de documento por GET para asegurar que expone el raw_content actualizado
        print("\n--- 5. Consultando Detalle del Documento ---")
        response = client.get(f"/api/documents/{doc_id}")
        assert response.status_code == 200, f"Error: {response.text}"
        detail_data = response.json()
        assert detail_data["raw_content"] == doc_payload_2["content"]
        print(f"Detalle verificado con éxito. Título: {detail_data['filename']}, Contenido: '{detail_data['raw_content']}'")

        print("\n[OK] ¡TODAS LAS PRUEBAS DE ACTUALIZACIÓN DE CONOCIMIENTO PASARON EXITOSAMENTE!\n")

if __name__ == "__main__":
    try:
        init_db()
        clean_database()
        run_kb_update_test()
    except AssertionError as ae:
        print(f"\n[FAIL] FALLÓ LA PRUEBA: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR INESPERADO: {e}")
        sys.exit(1)
    finally:
        clean_database()
