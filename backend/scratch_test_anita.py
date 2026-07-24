import asyncio
import os
import sys

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
        agent = db.query(Agent).filter(Agent.name == "Anita Gourmet").first()
        print(f"Testing Agent: {agent.name} (ID: {agent.id})")

        # Create temporary test conversation
        conv = Conversation(
            agent_id=agent.id,
            channel="web",
            contact_name="Cliente de Prueba",
            status="active"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        reply = await process_conversation_message(
            db=db,
            agent=agent,
            conversation=conv,
            user_message_text="Hola, buenas tardes. Quisiera cotizar una paella para un evento familiar de 15 personas el próximo sábado.",
            source_channel="web"
        )

        print("\n--- ANITA GOURMET RESPONSE ---")
        print(reply)
        print("------------------------------\n")

    except Exception as e:
        print("ERROR:", e)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test())
