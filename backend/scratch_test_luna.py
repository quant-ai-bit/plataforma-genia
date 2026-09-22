import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.agent import Agent
from models.conversation import Conversation
from services.conversation_service import process_conversation_message

DATABASE_URL = "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres"

async def test():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        agent = db.query(Agent).filter(Agent.name == "Luna").first()
        print(f"Testing Agent: {agent.name} (ID: {agent.id})")

        # Crear conversación de prueba
        conv = Conversation(
            agent_id=agent.id,
            channel="web",
            contact_name="Lau - Paciente Prueba",
            status="active"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        test_msg = "Hola buenas tardes, quisiera saber si el doctor atiende niños pequeños y si hace visitas a domicilio en Pereira."
        print(f"Mensaje de prueba: {test_msg}\n")

        reply = await process_conversation_message(
            db=db,
            agent=agent,
            conversation=conv,
            user_message_text=test_msg,
            source_channel="web"
        )

        print("--- RESPUESTA DE LUNA (IA) ---")
        print(reply)
        print("------------------------------\n")

    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test())
