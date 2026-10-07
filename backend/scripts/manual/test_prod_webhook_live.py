import asyncio
import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "gen-lang-client-0111526550"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/Users/User/.gcp/genia-vertex.json"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.agent import Agent
from models.conversation import Message as DBMessage
from routers.whatsapp import receive_qr_webhook

class MockRequest:
    def __init__(self, data):
        self._data = data
        
    async def json(self):
        return self._data

DATABASE_URL = "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres"

async def test_webhook():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        # Delete previous test message to bypass deduplication
        db.query(DBMessage).filter(DBMessage.whatsapp_message_id == "TEST_WEBHOOK_MSG_999").delete()
        db.commit()
        print("[TEST] Cleaned up previous test message.")

        payload = {
            "event": "messages.upsert",
            "instance": "genia_agent_547c07f714394e399c504d4bb3da37ac",
            "data": {
                "key": {
                    "remoteJid": "573103125460@s.whatsapp.net",
                    "fromMe": False,
                    "id": "TEST_WEBHOOK_MSG_999"
                },
                "message": {
                    "conversation": "Reiniciar"
                },
                "pushName": "Alejandro"
            }
        }
        
        print("[TEST] Calling receive_qr_webhook with payload...")
        req = MockRequest(payload)
        res = await receive_qr_webhook(
            agent_id="547c07f714394e399c504d4bb3da37ac",
            request=req,
            db=db
        )
        print("[TEST] Webhook response:", res)
    except Exception as e:
        import traceback
        print("[TEST] EXCEPTION THROWN:")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_webhook())
