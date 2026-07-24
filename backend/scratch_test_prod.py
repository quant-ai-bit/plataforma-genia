import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.conversation import Conversation, Message
from models.agent import Agent
from services.conversation_service import process_conversation_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres"

async def test():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        conv = db.query(Conversation).order_by(Conversation.last_message_at.desc()).first()
        agent = db.query(Agent).filter(Agent.id == conv.agent_id).first()
        print(f"Testing agent {agent.name} with user message 'Felipe'...")

        reply = await process_conversation_message(
            db=db,
            agent=agent,
            conversation=conv,
            user_message_text="Felipe",
            source_channel="whatsapp",
        )
        print("REPLY:", reply)
    except Exception as e:
        print("EXCEPTION:", type(e), e)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test())
