"""
Script de Pruebas de Integración para el Entrenamiento Visual Didáctico por Inputs en PLATAFORMA GENIA.

Verifica:
1. Creación de un agente de prueba.
2. Subida de imagen y generación de entrenamiento mediante inputs (Nombre, Descripción, Precio).
3. Confirmación del entrenamiento y modificación automática del prompt del sistema.
4. Eliminación de la imagen y limpieza automática de las instrucciones añadidas al prompt del sistema.
"""

import os
import sys
from fastapi.testclient import TestClient

# Cargar variables de entorno del backend
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from main import app
from database import SessionLocal, init_db
from models.agent import Agent
from models.agent_image import AgentImage
from models.conversation import Conversation, Message

client = TestClient(app)

def clean_database():
    """Limpia registros de prueba anteriores de la base de datos."""
    db = SessionLocal()
    try:
        # Eliminar registros de imágenes de prueba
        db.query(AgentImage).delete()
        # Eliminar mensajes
        db.query(Message).delete()
        # Eliminar conversaciones
        db.query(Conversation).delete()
        # Eliminar agentes de prueba creados
        db.query(Agent).filter(Agent.name == "Genia Didactic Test Bot").delete()
        db.commit()
        print("[CLEAN] Base de datos limpia de pruebas didácticas.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error limpiando: {e}")
    finally:
        db.close()

def run_didactic_test():
    print("\n[START] Iniciando Pruebas de Entrenamiento Visual Didáctico...\n")

    # --- 1. Crear Agente ---
    print("--- 1. Creando Agente de Prueba ---")
    agent_payload = {
        "name": "Genia Didactic Test Bot",
        "description": "Agente de prueba para flujo didáctico con inputs de usuario",
        "system_prompt": "Eres Genia Bot. Tu deber es responder a los clientes amablemente.",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.0,
        "max_tokens": 1024,
        "custom_fields": [],
        "channels": ["web"]
    }
    response = client.post("/api/agents/", json=agent_payload)
    assert response.status_code == 201, f"Error: {response.text}"
    agent_id = response.json()["id"]
    print(f"Agente creado exitosamente con ID: {agent_id}")

    # --- 2. Subir Imagen y Generar Entrenamiento ---
    print("\n--- 2. Subiendo Imagen con Datos Manuales de Usuario ---")
    dummy_png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xfc\xcf\xc0"
        b"\xf0\x1f\x00\x05\x80\x01\x01\x19\x18\xdd\x8d\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    
    file_payload = {
        "file": ("sala_juntas_vip.png", dummy_png_bytes, "image/png")
    }
    data_payload = {
        "product_name": "Sala de Juntas VIP",
        "description": "Espacio premium con mesa de vidrio templado y capacidad para 12 personas",
        "price": "$60.000 COP/hora"
    }

    # Llamar al nuevo endpoint
    response = client.post(
        f"/api/agents/{agent_id}/images/upload-and-generate-training",
        files=file_payload,
        data=data_payload
    )
    assert response.status_code == 201, f"Error: {response.text}"
    img_data = response.json()
    image_id = img_data["image_id"]
    image_url = img_data["url"]
    
    print(f"Imagen subida y procesada correctamente.")
    print(f"ID Imagen: {image_id}")
    print(f"URL: {image_url}")
    print(f"Producto Confirmado: {img_data['detected_product']}")
    print(f"Descripción combinada en DB: {img_data['description']}")
    print(f"Keywords sugeridas por LLM: {img_data['keywords']}")
    print(f"Regla de prompt sugerida por LLM:\n> {img_data['suggested_rule']}")

    # Validaciones
    assert img_data["detected_product"] == "Sala de Juntas VIP"
    assert "Sala de Juntas VIP" in img_data["description"]
    assert "$60.000 COP" in img_data["description"]
    assert img_data["suggested_rule"] != ""
    assert img_data["keywords"] != ""

    # --- 3. Confirmar Entrenamiento ---
    print("\n--- 3. Confirmando Entrenamiento y Actualizando Prompt ---")
    confirm_payload = {
        "description": img_data["description"],
        "detected_product": img_data["detected_product"],
        "keywords": img_data["keywords"],
        "suggested_rule": img_data["suggested_rule"],
        "add_to_prompt": True
    }
    
    response = client.post(
        f"/api/agents/{agent_id}/images/{image_id}/confirm-training",
        json=confirm_payload
    )
    assert response.status_code == 200, f"Error: {response.text}"
    print("Entrenamiento guardado y prompt del sistema actualizado con éxito.")

    # --- 4. Verificar Prompt de Sistema del Agente ---
    print("\n--- 4. Verificando System Prompt del Agente en BD ---")
    response = client.get(f"/api/agents/{agent_id}")
    assert response.status_code == 200
    agent_data = response.json()
    prompt = agent_data["system_prompt"]
    print(f"System Prompt Actualizado:\n{prompt}\n")
    
    assert f"<!-- START_IMAGE_RULE:{image_id} -->" in prompt
    assert f"<!-- END_IMAGE_RULE:{image_id} -->" in prompt
    assert f"![Sala de Juntas VIP]({image_url})" in prompt or image_url in prompt
    print("[OK] Prompt contiene las reglas delimitadas correctamente.")

    # --- 5. Eliminar la Imagen y verificar autolimpieza del Prompt ---
    print("\n--- 5. Eliminando la Imagen y Verificando Limpieza de Prompt ---")
    response = client.delete(f"/api/images/{image_id}")
    assert response.status_code == 200
    print("Imagen eliminada de base de datos y disco.")

    # Re-consultar agente para verificar que las reglas se autolimpiaron
    response = client.get(f"/api/agents/{agent_id}")
    assert response.status_code == 200
    agent_data = response.json()
    prompt_after = agent_data["system_prompt"]
    print(f"System Prompt después de eliminar imagen:\n{prompt_after}\n")
    
    assert f"<!-- START_IMAGE_RULE:{image_id} -->" not in prompt_after
    assert f"<!-- END_IMAGE_RULE:{image_id} -->" not in prompt_after
    assert "Sala de Juntas VIP" not in prompt_after
    assert prompt_after.strip() == "Eres Genia Bot. Tu deber es responder a los clientes amablemente."
    print("[OK] Las reglas del prompt fueron limpiadas automáticamente al eliminar la imagen.")

    print("\n[OK] ¡TODAS LAS PRUEBAS DIDÁCTICAS PASARON EXITOSAMENTE!\n")


if __name__ == "__main__":
    try:
        init_db()
        clean_database()
        run_didactic_test()
    except AssertionError as ae:
        print(f"\n[FAIL] FALLÓ LA PRUEBA: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR INESPERADO: {e}")
        sys.exit(1)
    finally:
        clean_database()
