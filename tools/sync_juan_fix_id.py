"""
Script para sincronizar y garantizar el ID exacto 04b0a43c8a814eae8c6e84124b9b6aa1
en Supabase PostgreSQL (Producción) con user_id asignado.
"""

import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.agent import Agent
from models.knowledge import KnowledgeDocument
from tools.create_agent_juan import JUAN_SYSTEM_PROMPT, JUAN_CUSTOM_FIELDS, KB_DOCUMENTS, SUPABASE_DB_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_ID = "04b0a43c8a814eae8c6e84124b9b6aa1"
USER_ID = "2d5fc55e-48e7-43bc-8d3e-624167bdae76"

def ensure_target_agent_in_supabase():
    engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. Buscar si ya existe el ID específico 04b0a43c8a814eae8c6e84124b9b6aa1
        agent = db.query(Agent).filter(Agent.id == TARGET_ID).first()

        if agent:
            logger.info("Agente con ID %s encontrado en Supabase. Actualizando...", TARGET_ID)
            agent.name = "Juan - A la mesa Juan cocina"
            agent.description = "Asistente virtual de atención al cliente y ventas de Ají Artesanal Mix de 7 Chiles en Pereira, Colombia."
            agent.system_prompt = JUAN_SYSTEM_PROMPT
            agent.provider = "vertex"
            agent.model = "gemini-2.5-flash"
            agent.temperature = 0.5
            agent.max_tokens = 2048
            agent.custom_fields = JUAN_CUSTOM_FIELDS
            agent.channels = ["web", "whatsapp"]
            agent.timezone = "America/Bogota"
            agent.user_id = USER_ID
        else:
            logger.info("Creando agente con ID exacto %s en Supabase...", TARGET_ID)
            agent = Agent(
                id=TARGET_ID,
                user_id=USER_ID,
                name="Juan - A la mesa Juan cocina",
                description="Asistente virtual de atención al cliente y ventas de Ají Artesanal Mix de 7 Chiles en Pereira, Colombia.",
                system_prompt=JUAN_SYSTEM_PROMPT,
                provider="vertex",
                model="gemini-2.5-flash",
                temperature=0.5,
                max_tokens=2048,
                custom_fields=JUAN_CUSTOM_FIELDS,
                channels=["web", "whatsapp"],
                notification_phone="+573209673284",
                whatsapp_provider="qr_code",
                stt_provider="groq_whisper",
                timezone="America/Bogota",
            )
            db.add(agent)

        db.commit()
        db.refresh(agent)
        logger.info("✅ Agente %s guardado exitosamente en Supabase. user_id=%s", agent.id, agent.user_id)

        # 2. Cargar Documentos de Base de Conocimiento
        for doc in KB_DOCUMENTS:
            existing_doc = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.agent_id == agent.id,
                KnowledgeDocument.filename == doc["filename"]
            ).first()

            if existing_doc:
                existing_doc.raw_content = doc["content"]
                existing_doc.chunk_count = len(doc["content"].split("\n\n"))
            else:
                new_doc = KnowledgeDocument(
                    agent_id=agent.id,
                    filename=doc["filename"],
                    content_type="text/plain",
                    raw_content=doc["content"],
                    chunk_count=len(doc["content"].split("\n\n")),
                )
                db.add(new_doc)

        db.commit()
        logger.info("✅ Base de conocimiento vinculada a %s exitosamente.", agent.id)

        # 3. También verificar si hay otros agentes 'Juan' sin user_id y actualizarlos
        other_juans = db.query(Agent).filter(Agent.name.ilike("%Juan%")).all()
        for j in other_juans:
            j.user_id = USER_ID
        db.commit()
        logger.info("✅ Todos los agentes Juan en Supabase actualizados con user_id=%s", USER_ID)

    except Exception as e:
        db.rollback()
        logger.error("❌ Error: %s", e, exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    ensure_target_agent_in_supabase()
